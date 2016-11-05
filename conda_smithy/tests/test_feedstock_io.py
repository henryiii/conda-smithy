from __future__ import unicode_literals

import functools
import io
import operator as op
import os
import stat
import shutil
import tempfile
import unittest

import git

import conda_smithy.feedstock_io as fio


def keep_dir(dirname):
    keep_filename = os.path.join(dirname, ".keep")
    with io.open(keep_filename, "w", encoding = "utf-8") as fh:
        fh.write("")


def parameterize():
    for pathfunc in [
        lambda pth, tmp_dir: os.path.relpath(pth, tmp_dir),
        lambda pth, tmp_dir: pth
    ]:
        for get_repo in [
            lambda tmp_dir: None,
            lambda tmp_dir: git.Repo.init(tmp_dir)
        ]:
            try:
                tmp_dir = tempfile.mkdtemp()
                keep_dir(tmp_dir)

                old_dir = os.getcwd()
                os.chdir(tmp_dir)

                yield (
                    tmp_dir,
                    get_repo(tmp_dir),
                    lambda pth: pathfunc(pth, tmp_dir)
                )
            finally:
                os.chdir(old_dir)
                shutil.rmtree(tmp_dir)


class TestFeedstockIO(unittest.TestCase):
    def setUp(self):
        self.old_dir = os.getcwd()

        self.tmp_dir = tempfile.mkdtemp()
        os.chdir(self.tmp_dir)

        with io.open(os.path.abspath(".keep"), "w", encoding="utf-8") as fh:
            fh.write("")


    def test_repo(self):
        for tmp_dir, repo, pathfunc in parameterize():
            if repo is None:
                self.assertTrue(
                    fio.get_repo(pathfunc(tmp_dir)) is None
                )
            else:
                self.assertIsInstance(
                    fio.get_repo(pathfunc(tmp_dir)),
                    git.Repo
                )


    def test_get_file_blob(self):
        for tmp_dir, repo, pathfunc in parameterize():
            if repo is None:
                continue

            filename = "test.txt"
            filename = os.path.join(tmp_dir, filename)

            with io.open(filename, "w", encoding = "utf-8") as fh:
                fh.write("")

            repo.index.add([filename])

            blob = None
            try:
                blob = fio.get_file_blob(repo, filename)
            except StopIteration:
                self.fail("Unable to find the file we added.")

            self.assertEqual(blob.name, os.path.basename(filename))


    def test_get_mode_file(self):
        perms = [
            stat.S_IWUSR,
            stat.S_IXUSR,
            stat.S_IRUSR,
            stat.S_IXGRP,
            stat.S_IRGRP,
            stat.S_IROTH
        ]

        set_mode = functools.reduce(op.or_, perms)

        for tmp_dir, repo, pathfunc in parameterize():
            filename = "test.txt"
            filename = os.path.join(tmp_dir, filename)
            with io.open(filename, "w", encoding = "utf-8") as fh:
                fh.write("")

            os.chmod(filename, set_mode)
            if repo is not None:
                blob = repo.index.add([filename])[0].to_blob(repo)
                blob.mode = set_mode
                repo.index.add([blob])

            file_mode = fio.get_mode_file(pathfunc(filename))
            self.assertEqual(file_mode & set_mode, set_mode)


    def tearDown(self):
        os.chdir(self.old_dir)
        del self.old_dir

        shutil.rmtree(self.tmp_dir)
        del self.tmp_dir


if __name__ == '__main__':
    unittest.main()
