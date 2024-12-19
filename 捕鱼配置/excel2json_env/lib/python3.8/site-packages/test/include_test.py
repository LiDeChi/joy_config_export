#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import unittest
from xml.etree import ElementTree as etree
import os
from proton import template

class TestIncludeFunctionality(unittest.TestCase):

    def setUp(self):
        template.base_dir = os.path.dirname(os.path.realpath(__file__))

    def test_include(self):
        tmp = template.get_template('include1.xhtml')

        tmp2 = template.get_template('include2.xhtml')
        
        tmp.set_value('title', 'Page Title')
        tmp.replace('include-content', tmp2)
        tmp.set_value('para1', 'First paragraph of text')
        tmp.set_value('para2', 'Second paragraph of text')

        out = str(tmp)
        print(out)

        et = etree.fromstring(out)

        self.assert_(et.find('body/h1').text == 'Page Title', 'incorrect heading')
        p = et.findall('body/div/p')
        self.assert_(len(p) == 2, 'should be 2 paragraphs')
        self.assert_(p[0].text == 'First paragraph of text', 'paragraph text incorrect')
        self.assert_(p[1].text == 'Second paragraph of text', 'paragraph text incorrect')

