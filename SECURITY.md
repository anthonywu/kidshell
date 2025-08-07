# Security Policy

## 🛡️ Security Features

kidshell implements multiple layers of security to protect users and admins in shared IT settings,
especially important given its target audience of children and educational environments.

### Path Traversal Protection

The application prevents directory traversal attacks that could allow unauthorized file system access:

- **Input Validation**: Blocks file names containing `..`, absolute paths (`/`, `\`), or Windows drive letters (`C:\`)
- **Path Resolution Validation**: Uses `pathlib.Path.relative_to()` to ensure all resolved paths stay within designated directories
- **Defense in Depth**: Multiple validation layers ensure security even if one check fails

**Implementation Details:**
- Location: `src/kidshell/core/config.py:109-134`
- Test Coverage: `tests/test_path_traversal_security.py`

### Safe JSON Processing

- Uses Python's built-in `json` module which is safe against code execution (unlike `pickle` or `yaml`)
- Implements file size limits to prevent memory exhaustion attacks
- Validates JSON structure before processing

### Subprocess Security

- Never uses `shell=True` in subprocess calls
- All subprocess commands use list arguments to prevent command injection
- Editor commands are validated against a safe allowlist
- Environment variables (EDITOR, VISUAL) are treated as trusted per OS security model

### File System Safety

- All file operations are confined to user-specific directories via `platformdirs`
- Creates files with safe defaults (`{}` for JSON files)
- Proper error handling prevents information leakage through stack traces
- Permission errors are caught and handled gracefully

## 🚨 Reporting Security Vulnerabilities

If you discover a security vulnerability in kidshell, please file an issue.

If `kidshell` gets traction in real edu environments, I will post a email for non-public responsible disclosure of vulnerabilities.

## 🔒 Security Best Practices for Users

### For Parents and Educators

1. **Run with Limited Privileges**: Never run kidshell with administrator/root privileges
2. **Monitor Custom Data**: Review any custom JSON data files before loading
3. **Use Platform Directories**: Let kidshell use platform-specific directories rather than custom paths
4. **Keep Updated**: Always use the latest version for security patches

### For Developers

1. **Input Validation**: All user input must be validated before use
2. **Path Operations**: Always use `pathlib` and validate paths stay within intended directories
3. **Subprocess Calls**: Never use `shell=True`, always use list arguments
4. **Error Handling**: Never expose system paths or sensitive information in error messages
5. **Dependencies**: Regularly update dependencies and monitor for security advisories

### Known Security Considerations

1. **Custom Data Files**: Users can load custom JSON files which could contain inappropriate content
   - **Mitigation**: Files are loaded from user-controlled directories only
   - **Recommendation**: Parents should review custom data files

2. **Editor Integration**: The application can launch external editors
   - **Mitigation**: Only launches editors from user's environment or safe allowlist
   - **Recommendation**: Set EDITOR environment variable to a trusted editor

3. **Mathematical Expression Evaluation**: Uses Python's `eval()` in controlled math context
   - **Mitigation**: Restricted namespace with only safe math functions
   - **Recommendation**: Monitor for unusual mathematical expressions

## 🧪 Security Testing

Run security tests with:

```bash
# Run path traversal security tests
python -m pytest tests/test_path_traversal_security.py -v

# Manual security validation
python -c "from kidshell.core.config import ConfigManager; c = ConfigManager(); c.edit_config('../../../etc/passwd')"
# Expected: Error: Invalid file name '../../../etc/passwd'
```

## 📚 Security Resources

- [OWASP Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [CWE-22: Path Traversal](https://cwe.mitre.org/data/definitions/22.html)
