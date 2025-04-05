# How to Hash a Log Page Password

Use `werkzeug.security` to generate a secure hash for the password:

```bash
python
```

```python
from werkzeug.security import generate_password_hash
print(generate_password_hash("YourPasswordHere"))
```

Then place the output into your `.env` file as:

```
LOGS_USER=yourusername
LOGS_PASSWORD_HASH=the_generated_hash
```
