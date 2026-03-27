PATH="$(pwd)/mock_bin:$PATH" bash test_exec2.sh >test.log 2>&1 || true
cat test.log
