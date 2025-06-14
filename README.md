# Sudamall Backend

A robust Django backend for the StoreBridge platform, providing secure user and store owner authentication with JWT and Google OAuth, account management, and store operation APIs.

---

## 🚀 Features

- **User Authentication**
  - Email/password login and registration
  - JWT-based authentication (access & refresh tokens)
  - Google OAuth2 login
  - OTP verification for sensitive actions

- **Business Owner Onboarding**
  - Business owner registration with store creation
  - Profile picture validation (type & size)
  - Phone and WhatsApp number validation

- **Account Management**
  - Password reset (request, verify, confirm)
  - User profile management

- **Store Management**
  - Store creation and assignment to business owners

- **Security**
  - Rate limiting/throttling on sensitive endpoints
  - Secure password handling
  - HttpOnly cookies for refresh tokens

- **API Documentation**
  - Interactive Swagger/OpenAPI docs via drf-spectacular

- **Asynchronous Tasks**
  - Celery integration for background jobs (e.g., sending emails)

---

## 🛠️ Tech Stack

- Python 3.12+
- Django 5.2+
- Django REST Framework
- drf-spectacular (OpenAPI/Swagger)
- SimpleJWT
- Celery & django-celery-beat
- PostgreSQL (recommended)
- Pillow (image handling)
- django-phonenumber-field

---

## ⚡ Quickstart

1. **Clone the repository**
   ```bash
   git clone [git@github.com:Code-for-sudan/back-end.git](https://github.com/Code-for-sudan/back-end.git)
   cd Code-for-sudan/back-end
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/dev.txt
   ```

4. **Configure environment variables**
   - Make sure all the env files in the app dir.

5. **Apply migrations**
   ```bash
   python manage.py makemigrations 
   python manage.py migrate
   ```

6. **Run the development server**
   ```bash
   DJANGO_ENV=dev python manage.py runserver
   ```

7. **Start Celery worker (in a separate terminal)**
   ```bash
   celery -A api worker --loglevel=info
   ```

8. **Start Celery beat (in a separate terminal)**
   ```bash
   celery -A api beat --loglevel=info
   ```

9. **Access API docs**
   - Visit [http://localhost:8000/api/schema/swagger-ui/](http://localhost:8000/api/schema/swagger-ui/)

---

## 🧪 Running Tests

```bash
python manage.py test
```

---

## 📚 API Documentation

- Interactive docs: `/api/schema/swagger-ui/`
- OpenAPI schema: `/api/schema/`

---

## 🤝 Contributing

Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on issues and pull requests.

---

## 📄 License

See [LICENSE](./LICENSE) for details.

---

## 📝 Acknowledgements

- [Django REST Framework](https://www.django-rest-framework.org/)
- [drf-spectacular](https://drf-spectacular.readthedocs.io/)
- [Celery](https://docs.celeryq.dev/en/stable/)
