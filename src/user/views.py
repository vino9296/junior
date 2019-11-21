from flask import (Blueprint, redirect, render_template, request, session,
                   url_for, flash)
from flask import current_app as junior_app
from flask.views import MethodView
from flask_mail import Message, Mail
from werkzeug.datastructures import MultiDict

from src.user.auth import SessionAuth
from src.user.forms import LoginForm, ProfileForm, RegistrationForm
from src.user.models import User
from src.views import BaseView


bp = Blueprint('auth', __name__, template_folder='templates')

class Registration(MethodView):

    def __init__(self, template_name):
        self.template: str = template_name
        self.form = RegistrationForm

    def post(self):
        form = self.form(request.form)
        if not form.validate():
            return render_template(self.template, **{'form': form})
        login = request.form.get('login')
        email = request.form.get('email')
        password = request.form.get('password')
        firstname = request.form.get('firstname')
        middlename = request.form.get('middlename')
        lastname = request.form.get('lastname')
        pass_hash = User.hash_password(password)
        user = User(
            login=login,
            email=email,
            password=pass_hash.decode(),
            firstname=firstname,
            middlename=middlename,
            lastname=lastname,
        )
        if User.query.filter_by(login=login).first():
            return render_template(
                self.template,
                **{'form': form, 'info': 'Логин уже занят'},
            )
        if User.query.filter_by(email=email).first():
            return render_template(
                self.template,
                **{'form': form, 'info': 'Email уже занят'},
            )
        msg = Message('Подтвердите регистрацию на JUNIOR, пройдя по ссылке',
                      sender=junior_app.config['ADMINS'][0],
                      recipients=[email]
                      )
        User.save(user)
        token = user.get_token_for_mail_aproved()
        msg.html = render_template('email_aprove.html',
                                   user=user, token=token)
        mail = Mail(junior_app)
        print('----------------------------')
        print(junior_app.config["MAIL_SERVER"])
        print(junior_app.config["MAIL_PORT"])
        print(junior_app.config["MAIL_USE_TLS"])
        print(junior_app.config["MAIL_USERNAME"])
        print(junior_app.config["MAIL_PASSWORD"])
        print(junior_app.config["ADMINS"])
        mail.send(msg)

        flash('Вам на почту отправлена ссылка для подтверждения регистрации')
        return redirect(url_for('auth.login'))

    def get(self):
        return render_template(self.template, **{'form': self.form()})


class Login(MethodView):
    def __init__(self, template_name):
        self.template = template_name
        self.form = LoginForm

    def get(self):
        return render_template(self.template, **{'form': self.form()})

    def post(self):
        form = self.form(request.form)

        if not form.validate():
            return render_template(self.template, **{'form': form})

        login = request.form['login']
        password = request.form['password']
        user = User.query.filter_by(
            login=login,
        ).first()
        if user and User.check_password(user, password):
            if not user.is_oauth:
                flash("Завершите регистрацию, пройдя по ссылке, отправленной на почту")
                return redirect(url_for('auth.login'))
            session['auth'] = SessionAuth(True, user)
        return redirect('/')


class Profile(BaseView):
    def __init__(self, template_name):
        super().__init__(template_name)
        self.form = ProfileForm

    def get(self):
        user = User.query.filter_by(login=session['auth'].user.login).first()
        user_data = MultiDict([
            ('email', user.email),
            ('firstname', user.firstname),
            ('middlename', user.middlename),
            ('lastname', user.lastname),
        ])
        self.context['form'] = self.form(user_data)
        return render_template(self.template_name, **self.context)

    def post(self):
        form = self.form(request.form)
        if not form.validate():
            return render_template(self.template, **{'form': form})
        User.query.filter_by(login=session['auth'].user.login).update({
            'email': request.form.get('email'),
            'firstname': request.form.get('firstname'),
            'middlename': request.form.get('middlename'),
            'lastname': request.form.get('lastname'),
        })
        return redirect(url_for('auth.profile'))


class Logout(MethodView):
    def get(self):
        auth = session.get('auth')
        auth.logout()
        return redirect(url_for('index.index'))


class EmailAprove(MethodView):
    """ Функция проверки ссылки, по которой переходит
    пользователь, завершая регистрацию """

    def get(self, token):
        user = User.verify_token_for_mail_aproved(token)
        print(f'Проверен токен {token} для пользователя {user}')
        if not user:
            return redirect(url_for('index.index'))
        return redirect(url_for('auth.login'))


bp.add_url_rule(
    '/logout/',
    view_func=Logout.as_view(
        name='logout',
    ),
)

bp.add_url_rule(
    '/registration/',
    view_func=Registration.as_view(
        name='registration',
        template_name='register_form.jinja2',
    ),
)
bp.add_url_rule(
    '/login/',
    view_func=Login.as_view(
        name='login',
        template_name='login.jinja2',
    ),
)
bp.add_url_rule(
    '/profile/',
    view_func=Profile.as_view(
        name='profile',
        template_name='profile_form.jinja2',
    ),
)

bp.add_url_rule(
    '/email_aprove/<token>',
    view_func=EmailAprove.as_view(
        name='email_aprove',
    ),
)
