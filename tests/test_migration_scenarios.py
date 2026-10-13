"""Opt-in complete builds; selected integration profiles fail on missing prerequisites."""

import os
import unittest

from scripts.run_migration_scenarios import Scenarios, parse_args


@unittest.skipUnless(os.environ.get("JAVA_MODERNIZE_E2E") == "1", "Enable the explicit full-build integration profile")
class CompleteMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        args, selected = parse_args([])
        cls.runner = Scenarios(args)
        cls.runner.verify_tools(selected)

    def test_actual_java8_to25_multi_module_runtime_migration(self):
        result = self.runner.java_reactor()
        self.assertEqual((result["baseline_jdk"], result["after_jdk"]), (8, 25))

    def test_same_java_framework_patch(self):
        result = self.runner.spring(False)
        self.assertEqual(result["selected_boot"], "3.5.16")

    def test_framework_major_and_test_api_migration(self):
        result = self.runner.spring(True)
        self.assertTrue(result["selected_boot"].startswith("4.0."))

    def test_gradle_groovy_catalog_and_locks(self):
        self.assertTrue(self.runner.gradle("groovy")["idempotent"])

    def test_gradle_kotlin_catalog_and_locks(self):
        self.assertTrue(self.runner.gradle("kotlin")["idempotent"])
