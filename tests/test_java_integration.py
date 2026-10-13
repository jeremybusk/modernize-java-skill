"""Compile/run controlled Java fixtures to validate actual target and contract behavior."""

import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import unittest


class JavaIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.javac, cls.java = shutil.which("javac"), shutil.which("java")
        if not cls.javac or not cls.java:
            if os.environ.get("JAVA_MODERNIZE_REQUIRE_JDK") == "1":
                raise RuntimeError("CI requires javac and java")
            raise unittest.SkipTest("Requires JDK 17+ for Java fixture verification")
        result = subprocess.run([cls.javac, "-version"], capture_output=True, text=True, check=True, timeout=30)
        match = re.search(r"javac (\d+)", result.stdout + result.stderr)
        if not match or int(match.group(1)) < 17:
            if os.environ.get("JAVA_MODERNIZE_REQUIRE_JDK") == "1":
                raise RuntimeError("CI requires JDK 17+")
            raise unittest.SkipTest("Requires JDK 17+")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def compile(self, name, source, release):
        path = self.root / (name + ".java")
        path.write_text(source, encoding="utf-8")
        return subprocess.run([self.javac, "--release", str(release), "-d", str(self.root), str(path)], capture_output=True, text=True, timeout=60)

    def run_class(self, name):
        return subprocess.run([self.java, "-cp", str(self.root), name], capture_output=True, text=True, timeout=30)

    def test_java11_api_target_emits_correct_bytecode_and_preserves_contracts(self):
        source = '''import java.util.*;
import java.util.stream.*;
import javax.sql.DataSource;
public class ContractFixture {
  DataSource dataSource;
  public static void main(String[] args) {
    List<String> list = Stream.of("a", (String)null).collect(Collectors.toCollection(ArrayList::new));
    list.add("extra");
    if (list.size() != 3 || list.get(1) != null) throw new AssertionError("list contract");
    if (!"\\u0000".trim().isEmpty() || "\\u0000".isBlank()) throw new AssertionError("control whitespace");
    if ("\\u2003".trim().isEmpty() || !"\\u2003".isBlank()) throw new AssertionError("Unicode whitespace");
    try { List.of("a", (String)null); throw new AssertionError("null policy"); }
    catch (NullPointerException expected) {}
  }
}'''
        compiled = self.compile("ContractFixture", source, 11)
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        raw = (self.root / "ContractFixture.class").read_bytes()
        self.assertEqual(struct.unpack(">H", raw[6:8])[0], 55)
        run = self.run_class("ContractFixture")
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_compiler_cannot_use_newer_api_under_old_release(self):
        source = 'public class NewApi { Object names() { return java.util.stream.Stream.of("a").toList(); } }'
        compiled = self.compile("NewApi", source, 11)
        self.assertNotEqual(compiled.returncode, 0)
        self.assertFalse((self.root / "NewApi.class").exists())

    def test_record_requires_newer_target_and_stream_result_is_unmodifiable(self):
        source = '''public record RecordFixture(String name) {
  public static void main(String[] args) {
    var names = java.util.stream.Stream.of("a").toList();
    try { names.add("b"); throw new AssertionError("mutability"); }
    catch (UnsupportedOperationException expected) {}
    if (!new RecordFixture("x").name().equals("x")) throw new AssertionError();
  }
}'''
        rejected = self.compile("RecordFixture", source, 11)
        self.assertNotEqual(rejected.returncode, 0)
        accepted = self.compile("RecordFixture", source, 17)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        run = self.run_class("RecordFixture")
        self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == "__main__":
    unittest.main()
