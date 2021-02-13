from setuptools import setup, find_packages

setup(
    name='phps_sms',
    version='0.1',
    url='https://github.com/kkyubrother/Phps_sms',
    license=' Apache-2.0 License',
    author='Kkyubrother',
    author_email='kkyubrother@naver.com',
    description='Php School SMS module',
    packages=find_packages(),
    zip_safe=False,
    setup_requires=['requests>=2.25.1', 'phpserialize>=1.3'],
)