#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import re
import random
import webapp2
import jinja2
from google.appengine.ext import db
import urllib2
from xml.dom import minidom
from string import letters
from google.appengine.api import memcache
import logging
import sys

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)


class Art(db.Model):
    title = db.StringProperty(required = True)
    art = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    coords = db.GeoPtProperty()

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

IP_URL ="http://api.hostip.info/?ip="

def get_coords(ip):
    #ip="4.2.2.2"
    url = IP_URL+ip
    content=None
    try:
        content = urllib2.urlopen(url).read()
    except urllib2.URLError:
        return

    if content:
        d=minidom.parseString(content)
        coords = d.getElementsByTagName("gml:coordinates")
        if coords and coords[0].childNodes[0].nodeValue:
            lon, lat = coords[0].childNodes[0].nodeValue.split(',')
            return db.GeoPt(lat,lon)

GMAPS_URL = "http://maps.googleapis.com/maps/api/staticmap?size=380x263&sensor=false&"

def gmaps_img(points):
    markers = '&'.join('markers=%s,%s' %(p.lat, p.lon) for p in points)
    return GMAPS_URL+markers

def top_arts(update=False):
    key='top'
    arts= memcache.get(key)
    if update or arts is None:
        
        arts = db.GqlQuery("SELECT * FROM Art ORDER BY created DESC")
        arts=list(arts)
        memcache.set(key, arts)
    return arts
        

class MainPage(Handler):
    def render_front(self, title="", art="", error=""):
        arts = top_arts()
        img_url = None
        points=  filter(None, (a.coords for a in arts))
        
        if points:
            img_url = gmaps_img(points)
            
                
        self.render("front.html", title=title, art=art, error = error, arts = arts, img_url=img_url)


    def get(self):
 
        self.render_front()

        
    def post(self):
        title = self.request.get("title")
        art = self.request.get("art")
        if title and art:
            a = Art(title = title, art = art)
            coords = get_coords(self.request.remote_addr)
            if coords:
                a.coords = coords
            a.put()
            top_arts(True)
            self.redirect("/")
        else:
            error = "We need both a title and some artwork!"
            self.render_front(title, art, error)



app = webapp2.WSGIApplication([('/', MainPage)], debug=True)
