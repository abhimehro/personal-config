#!/bin/bash
mkdir -p mybin
cat > mybin/mytool << 'IN'
#!/bin/bash
/bin/echo "mocked"
IN
chmod +x mybin/mytool
PATH="$(pwd)/mybin:$PATH" bash -c 'mytool'
