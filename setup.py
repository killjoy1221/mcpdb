from setuptools import setup

setup(
    name="mcpdb",
    packages=["mcpdb"],
    python_requires=">=3.7",
    install_requires=[
        'flask',
        'flask-httpauth',
        'flask-restplus',
        'github-flask',
        'flask_sqlalchemy',
        'sqlalchemy',
        'sqlalchemy_utils',
        'passlib',
        'werkzeug',
        'requests',
        'click',
        'itsdangerous'
    ]
)
