# This file is part of Copernicus
# http://www.copernicus-computing.org/
# 
# Copyright (C) 2011, Sander Pronk, Iman Pouya, Erik Lindahl, and others.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published 
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


from distutils.core import setup

setup(
      name='cpc',
      version='0.01dev',
      packages=['cpc',
                'cpc.client', 
                'cpc.client.view', 
                'cpc.controller', 
                'cpc.controller.project', 
                'cpc.network', 
                'cpc.network.com', 
                'cpc.network.http', 
                'cpc.server', 
                'cpc.server.command', 
                'cpc.server.heartbeat', 
                'cpc.server.project', 
                'cpc.server.request', 
                'cpc.server.spec', 
                'cpc.server.state', 
                'cpc.server.task', 
                'cpc.test', 
                'cpc.test.functional', 
                'cpc.util', 
                'cpc.util.log', 
                'cpc.util.plugin',
                'cpc.util.conf' 
                'cpc.worker' ],
      #package_dir={ 'copernicus' : 'copernicus'} ,
      scripts=['cpcc','cpc-server','cpc-worker'],
      license='TBD',
      long_description=open('README.txt').read(),
     )

