import concurrent.futures
import unittest

import aircontrol.py315_compat  # noqa: F401


class Py315CompatTests(unittest.TestCase):
    def test_thread_pool_is_a_real_class(self):
        executor_cls = concurrent.futures.ThreadPoolExecutor
        self.assertTrue(isinstance(executor_cls, type))
        with executor_cls(max_workers=1) as pool:
            self.assertEqual(pool.submit(lambda: 42).result(), 42)

    def test_namespace_has_no_lazy_placeholders(self):
        for name, value in vars(concurrent.futures).items():
            self.assertNotEqual(type(value).__name__, "lazy_import", name)


if __name__ == "__main__":
    unittest.main()
