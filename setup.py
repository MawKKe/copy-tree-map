from setuptools import setup, find_packages
import pkg_resources
import pathlib

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / 'README.md').read_text(encoding='utf-8')

requirements = []

extras_require = {
    'dev': [
        'pytest',
        'pytest-cov',
        'pytest-flake8'
    ]
}

if __name__ == "__main__":
    setup(
        name="copy-tree-map",
        version='0.1.0',
        description='Clone a directory tree while possibly filtering and/or transforming files',
        long_description=long_description,
        long_description_content_type='text/markdown',
        url='https://github.com/MawKKe/copy-tree-map',
        author='Markus H (MawKKe)',
        author_email='markus@mawkke.fi',
        license='Apache 2.0',
        package_date={'': ['LICENSE']},
        py_modules=["copy_tree_map"],
        entry_points={
            'console_scripts': {
                'copy-tree-map=copy_tree_map:main'
            }
        },
        python_requires='>=3.5, <4',
        install_requires=requirements,
        extras_require=extras_require,
        project_urls={
            'Bug reports': 'https://github.com/MawKKe/copy-tree-map/issues',
            'Source': 'https://github.com/MawKKe/copy-tree-map'
        },
    )
