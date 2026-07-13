"""Regression tests for language detection, extension resolution, and execution dispatch."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.language_engine import (
    LanguageDetector, ExtensionResolver, ExecutionDispatcher,
    CompilerManager, LanguageDef,
)


def test_language_detection():
    cases = [
        ("Create hello world in Python", "python", ".py"),
        ("Create palindrome in C++", "cpp", ".cpp"),
        ("Create palindrome in C", "c", ".c"),
        ("Create calculator in Java", "java", ".java"),
        ("Create webpage", "html", ".html"),
        ("Write a JavaScript function", "javascript", ".js"),
        ("Create a Go program", "go", ".go"),
        ("Write Rust code", "rust", ".rs"),
        ("Create a PHP script", "php", ".php"),
        ("Make a TypeScript file", "typescript", ".ts"),
        ("Create a C# application", "csharp", ".cs"),
        ("Write Kotlin code", "kotlin", ".kt"),
        ("Swift mobile app", "swift", ".swift"),
        ("Ruby script", "ruby", ".rb"),
        ("Bash script", "bash", ".sh"),
        ("CSS stylesheet", "css", ".css"),
        ("React component", "react", ".jsx"),
        ("Create a program", "python", ".py"),  # fallback to python
        ("Create a C++ file called palindrome.cpp", "cpp", ".cpp"),
        ("Write a py script", "python", ".py"),
        ("Make a js file", "javascript", ".js"),
    ]
    passed = 0
    failed = 0
    for prompt, expected_lang, expected_ext in cases:
        lang = LanguageDetector.detect(prompt)
        ext_ok = lang.extension == expected_ext
        lang_ok = lang.name == expected_lang
        if lang_ok and ext_ok:
            passed += 1
            print(f"  PASS: '{prompt}' -> {lang.name} ({lang.extension})")
        else:
            failed += 1
            print(f"  FAIL: '{prompt}' -> got {lang.name} ({lang.extension}), expected {expected_lang} ({expected_ext})")
    print(f"\nLanguage detection: {passed}/{passed+failed} passed")
    return failed == 0


def test_extension_resolution():
    cases = [
        ("python", ".py", "hello.py", "hello.py"),
        ("cpp", ".cpp", "palindrome.py", "palindrome.cpp"),  # fix wrong extension
        ("java", ".java", "Calculator.java", "Calculator.java"),
        ("javascript", ".js", "server.js", "server.js"),
        ("html", ".html", "index.html", "index.html"),
    ]
    passed = 0
    failed = 0
    from app.services.language_engine import _NAME_TO_DEF
    for lang_name, expected_ext, explicit_fn, expected_fn in cases:
        lang = _NAME_TO_DEF[lang_name]
        result = ExtensionResolver.resolve(lang, explicit_fn)
        if result == expected_fn:
            passed += 1
            print(f"  PASS: resolve({lang_name}, {explicit_fn}) -> {result}")
        else:
            failed += 1
            print(f"  FAIL: resolve({lang_name}, {explicit_fn}) -> got {result}, expected {expected_fn}")
    print(f"\nExtension resolution: {passed}/{passed+failed} passed")
    return failed == 0


def test_filename_generation():
    cases = [
        ("palindrome", "cpp", "palindrome.cpp"),
        ("hello world", "python", "hello_world.py"),
        ("calculator", "java", "calculator.java"),
        ("my server", "javascript", "my_server.js"),
    ]
    passed = 0
    failed = 0
    from app.services.language_engine import _NAME_TO_DEF
    for topic, lang_name, expected in cases:
        lang = _NAME_TO_DEF[lang_name]
        result = ExecutionDispatcher.build_filename(topic, lang)
        if result == expected:
            passed += 1
            print(f"  PASS: build_filename({topic}, {lang_name}) -> {result}")
        else:
            failed += 1
            print(f"  FAIL: build_filename({topic}, {lang_name}) -> got {result}, expected {expected}")
    print(f"\nFilename generation: {passed}/{passed+failed} passed")
    return failed == 0


def test_execution_dispatch():
    output_dir = "C:\\Users\\ACO_Output"
    cases = [
        ("python", "hello.py", "python \"C:\\Users\\ACO_Output\\hello.py\""),
        ("javascript", "server.js", "node \"C:\\Users\\ACO_Output\\server.js\""),
        ("java", "Calculator.java", "java -cp \"C:\\Users\\ACO_Output\" Calculator"),
        ("go", "main.go", "go run \"C:\\Users\\ACO_Output\\main.go\""),
        ("php", "script.php", "php \"C:\\Users\\ACO_Output\\script.php\""),
        ("ruby", "test.rb", "ruby \"C:\\Users\\ACO_Output\\test.rb\""),
        ("html", "index.html", "echo \"File saved"),
        ("bash", "run.sh", "bash \"C:\\Users\\ACO_Output\\run.sh\""),
    ]
    passed = 0
    failed = 0
    from app.services.language_engine import _NAME_TO_DEF
    for lang_name, filename, expected_prefix in cases:
        lang = _NAME_TO_DEF[lang_name]
        filepath = os.path.join(output_dir, filename)
        result = ExecutionDispatcher.run_command(filepath, lang, output_dir)
        if result.startswith(expected_prefix):
            passed += 1
            print(f"  PASS: run_command({filename}, {lang_name}) -> {result[:80]}")
        else:
            failed += 1
            print(f"  FAIL: run_command({filename}, {lang_name}) -> {result[:80]}")
            print(f"         expected prefix: {expected_prefix[:80]}")
    print(f"\nExecution dispatch: {passed}/{passed+failed} passed")
    return failed == 0


def test_compile_commands():
    output_dir = "C:\\Users\\ACO_Output"
    cases = [
        ("c", "hello.c", "gcc"),
        ("cpp", "hello.cpp", "g++"),
        ("java", "Hello.java", "javac"),
        ("rust", "main.rs", "rustc"),
        ("python", "hello.py", None),  # no compile needed
        ("javascript", "server.js", None),  # no compile needed
        ("html", "index.html", None),  # no compile needed
    ]
    passed = 0
    failed = 0
    from app.services.language_engine import _NAME_TO_DEF
    for lang_name, filename, expected_compiler in cases:
        lang = _NAME_TO_DEF[lang_name]
        filepath = os.path.join(output_dir, filename)
        result = ExecutionDispatcher.compile_command(filepath, lang, output_dir)
        actual_compiler = result[0] if result else None
        if actual_compiler == expected_compiler:
            passed += 1
            print(f"  PASS: compile({filename}, {lang_name}) -> compiler={actual_compiler}")
        else:
            failed += 1
            print(f"  FAIL: compile({filename}, {lang_name}) -> got compiler={actual_compiler}, expected {expected_compiler}")
    print(f"\nCompile commands: {passed}/{passed+failed} passed")
    return failed == 0


def test_no_python_default_for_cpp():
    """Regression: 'create a cpp file for palindrome' must NOT produce .py"""
    lang = LanguageDetector.detect("create a cpp file for palindrome in my desktop")
    assert lang.name == "cpp", f"Expected cpp, got {lang.name}"
    assert lang.extension == ".cpp", f"Expected .cpp, got {lang.extension}"
    filename = ExecutionDispatcher.build_filename("palindrome", lang)
    assert filename.endswith(".cpp"), f"Expected .cpp, got {filename}"
    run_cmd = ExecutionDispatcher.run_command(
        os.path.join("C:\\Output", filename), lang, "C:\\Output"
    )
    assert "g++" not in run_cmd or ".exe" in run_cmd, f"C++ should compile, not interpret: {run_cmd}"
    print(f"  PASS: C++ regression — filename={filename}, run={run_cmd[:80]}")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("LANGUAGE ENGINE REGRESSION TESTS")
    print("=" * 60)
    results = []
    results.append(("Language Detection", test_language_detection()))
    results.append(("Extension Resolution", test_extension_resolution()))
    results.append(("Filename Generation", test_filename_generation()))
    results.append(("Execution Dispatch", test_execution_dispatch()))
    results.append(("Compile Commands", test_compile_commands()))
    results.append(("C++ Regression", test_no_python_default_for_cpp()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {name}: {status}")
        if not ok:
            all_pass = False
    print(f"\nOverall: {'ALL PASSED' if all_pass else 'SOME FAILED'}")
    sys.exit(0 if all_pass else 1)
