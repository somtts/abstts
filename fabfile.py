"""
Copyright (C) 2014 wak

Licensed under the Apache License, Version 2.0 (the 'License');
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an 'AS IS' BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from __future__ import print_function
import os

import json
import xml.etree
from xml.etree.ElementTree import ElementTree, Element

from fabric.api import *
from fabric.colors import *


ENCODING = 'UTF-8'
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT_DIR = os.path.join(ROOT_DIR, 'app')
APP_RES_DIR = os.path.join(APP_ROOT_DIR, 'src/main/res')
CREDENTIALS_DIR = os.path.join(ROOT_DIR, 'credentials')
RELEASE_KEYSTORE = os.path.join(CREDENTIALS_DIR, 'release.keystore')
DPI = {'xhdpi': 2,
       'xxhdpi': 3,
       'xxxhdpi': 4}


@task
def init():
    clean()
    local('mkdir -p ' + CREDENTIALS_DIR)
    if not os.path.exists(RELEASE_KEYSTORE) and prompt('Create release.keystore? [y/n]') == 'y':
        generate_keystore(RELEASE_KEYSTORE)


@task
def prepare_for_commit():
    _cleanup_inkscape_svg(os.path.join(ROOT_DIR, 'files/logomark.svg'))
    local('rm -rf %s' % os.path.join(APP_ROOT_DIR, 'build'))
    validation(False)


@task
def validation(verbose=False):
    """ validation:{verbose=False} """
    print('Validating files...')
    fails = []
    for root, dirs, files in os.walk(os.path.join(APP_ROOT_DIR, 'src')):
        for filename in files:
            fullpath = os.path.join(root, filename)
            result = 'OK'
            run_validation = False
            try:
                run_validation = _validates_file(fullpath, verbose)
            except Exception as e:
                fails.append((fullpath, e))
    if not fails:
        print('All items are valid')
    for fail in fails:
        print(red('{} ... {}'.format(*fail)))
                    
                

@task
def generate_keystore(keystore):
    """ generate_keystore:{keystore} """
    if os.path.exists(keystore):
        print(yellow('{} is already exists'.format(keystore)))
        return
    if keystore:
        print('keystore: ' + keystore)
    else:
        keystore = prompt('keystore: ')
    alias = prompt('alias: ')
    local(('keytool -genkey -v'
           ' -keystore {keystore} -alias {alias}'
           ' -keyalg RSA -keysize 2048 -validity 10000').format(**locals()))
    props_path = keystore + '.properties'
    if os.path.exists(props_path):
        return
    with open(props_path, 'w') as f:
        f.write(("storeFile={keystore}\n"
                 "storePassword=dummy\n"
                 "keyAlias={alias}\n"
                 "keyPassword=dummy").format(keystore=keystore, alias=alias))


@task
def clean():
    local('{}/gradlew clean packageDebug'.format(ROOT_DIR))
    local('rm -rf {}'.format(os.path.join(ROOT_DIR, 'androidapp-androidapp/build/*')))
    _clean_garbages()
    _clean_gradle_caches()


def _clean_garbages():
    for ext in ('pyc', 'swp'):
        local('find ' + ROOT_DIR + " -type f -name '*." + ext + "' -exec rm -rf {} ';'")
    for filename in ('.DS_Store', ):
        local('find ' + ROOT_DIR + " -type f -name '" + filename + "' -exec rm -rf {} ';'")


def _clean_gradle_caches():
    """
    [Gradle 0.7.0] Build fails with: Duplicate files copied in APK META-INF/LICENSE.txt
    https://groups.google.com/forum/#!topic/adt-dev/bl5Rc4Szpzg
    """
    patterns = ['META-INF/' + i for i
                in ['NOTICE*', 'LICENSE*', 'notice.txt', 'license.txt*']]
    patterns.append('LICENSE.txt')

    for pattern in patterns:
        local("find ~/.gradle/caches/"
              " -iname \'*.jar\' -exec zip -d '{}' '" + pattern + "' \\;")


def _validates_file(path, log=False):
    ext = os.path.splitext(path)[1]
    if ext in ['.svg', '.xml']:
        if log:
            print('validate as XML: ' + path)
        xml.etree.ElementTree.parse(path)
        return True
    if ext == '.json':
        if log:
            print('validate as JSON: ' + path)
        json.load(open(path, 'r'))
        return True
    return False


def _cleanup_inkscape_svg(svg_path):
    print('Cleaning inkscape svg...')
    ns_dict = {'osb': 'http://www.openswatchbook.org/uri/2009/osb',
               'dc': 'http://purl.org/dc/elements/1.1/',
               'cc': 'http://creativecommons.org/ns#',
               'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
               'svg': 'http://www.w3.org/2000/svg',
               'xlink': 'http://www.w3.org/1999/xlink',
               'sodipodi': 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd',
               'inkscape': 'http://www.inkscape.org/namespaces/inkscape'}
    for key in ns_dict:
        xml.etree.ElementTree.register_namespace(key, ns_dict[key])

    tree = ElementTree()
    svg = tree.parse(svg_path)
    filename_attr = '{%s}export-filename' % ns_dict['inkscape']
    for g in svg.findall('{%s}g' % ns_dict['svg']):
        for element in g.findall('*'):
            if filename_attr in element.attrib:
                element.attrib[filename_attr] = ''
    tree.write(svg_path, encoding=ENCODING)
