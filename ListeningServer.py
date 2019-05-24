from flask import Flask, request, abort
from flask_cors import CORS
from email.message import EmailMessage
from arcgis import GIS
import smtplib
import ssl
import json
import re
import datetime

item_templates = None
with open('itemTemplates.json') as json_data:
    item_templates = json.load(json_data)

email_config = None
with open('emailConfig.json') as json_data:
    email_config = json.load(json_data)

app_credentials = None
with open('appCredentials.json') as json_data:
    app_credentials = json.load(json_data)

gis = None
app = Flask(__name__)
CORS(app)


@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST' or request.method == 'GET':
        try:
            info = request.json['info']
            portal_url = info['portalURL']
            events = request.json['events']
            for event in events:
                handle_event(event, portal_url)
        except KeyError:
            pass
        return '', 200
    else:
        abort(400)


def handle_event(event, portal_url):
    username = event['username']
    user_id = event['userId']
    item_id = event['id']
    when = event['when']
    operation = event['operation']
    source = event['source']
    if source == 'item':
        init_GIS(portal_url)
        needed_for_template = check_item(item_id)
        if needed_for_template:
            send_email(event, portal_url, needed_for_template)
    elif source == 'group':
        pass # implement this later
    elif source == 'user':
        pass # implement this later


def check_item(item_id):
    item = gis.content.get(item_id)
    item_data = item.get_data()
    needed_for_template = []
    for item_template in item_templates['templates']:
        needed = {}
        
        # props
        needed_tags = compare_tags(item_template['tags'], item.tags)
        if len(needed_tags) != 0:
            needed['tags'] = needed_tags

        needed_description_strings = compare_substring_list(item_template['description_substrings'], item.description)
        if len(needed_description_strings) != 0:
            needed['description_strings'] = needed_description_strings

        needed_title_strings = compare_substring_list(item_template['title_substrings'], item.title)
        if len(needed_title_strings) != 0:
            needed['title_strings'] = needed_title_strings

        needed_type = compare_property(item_template['type'], item.type)
        if needed_type:
            needed['type'] = needed_type

        needed_access = compare_property(item_template['access'], item.access)
        if needed_access:
            needed['access'] = needed_access

        # data props
        item_data_template = item_template['data']
        needed_layers = compare_layers(item_data_template['operationalLayers'], item_data['operationalLayers'])
        if needed_layers:
            needed['layers'] = needed_layers

        needed_basemap_layers = compare_layers(item_data_template['baseMap']['baseMapLayers'], item_data['baseMap']['baseMapLayers'])
        if needed_basemap_layers:
            needed['basemapLayers'] = needed_basemap_layers
            
        needed_SR = compare_property(item_data_template['spatialReference']['wkid'], item_data['spatialReference']['wkid'])
        if needed_SR:
            needed['SR'] = needed_SR

        if needed == {}:
            return None
        else:
            needed_for_template.append(needed)
    return needed_for_template


def compare_property(template_prop, prop):
    if template_prop != prop:
        return template_prop
    else:
        return None


def compare_tags(template_tags, tags):
    needed_tags = []
    for template_tag in template_tags:
        if template_tag not in tags:
            needed_tags.append(template_tag)
    return needed_tags


def compare_layers(template_layers, layers):
    needed_layers = []
    for template_layer in template_layers:
        match = False
        for layer in layers:
            if layer['url'] == template_layer['url']:
                match = True
        if not match:
            needed_layers.append(template_layer['url'])
    return needed_layers


def compare_substring_list(template_substrings, actual_string):
    needed_strings = []
    for template_substring in template_substrings:
        if not actual_string or not find_substring(template_substring, actual_string):
            needed_strings.append(template_substring)
    return needed_strings


def find_substring(substring, string):
    if string.find(substring) >= 0:
        return True
    else:
        return False


def init_GIS(portal_url):
    global gis
    gis = GIS(
        url=portal_url, 
        username=app_credentials['username'],
        password=app_credentials['password'], 
        verify_cert=False)


# send email
def send_email(event, portal_url, needed_for_template):
    username = event['username']
    user_id = event['userId']
    item_id = event['id']
    when = event['when']
    operation = event['operation']
    source = event['source']
    item_url = '{0}sharing/rest/content/items/{1}'.format(portal_url, item_id)

    port = email_config['port']

    message = EmailMessage()
    message['From'] = email_config['sender']
    message['To'] = email_config['recipients']
    message['Subject'] = email_config['subject']

    ts_date = datetime.datetime.fromtimestamp(when/1e3)
    content = 'An {0} operation occurred at {1} for {2} at {3}'.format(operation, ts_date.strftime('%Y-%m-%d %H:%M:%S'), source, item_url)
    content += '\n\nThere was a mismatch in metadata.'
    content += ' To meet the standards that you have set, you must make one of the following sets of changes:\n'
    joiner = ', '
    needed_ctr = 0
    for needed in needed_for_template:
        if 'layers' in needed:
            content += '\n\tAdd layers: {}'.format(joiner.join(needed['layers']))
        if 'basemapLayers' in needed:
            content += '\n\tAdd basemap layers: {}'.format(joiner.join(needed['basemapLayers']))
        if 'tags' in needed:
            content += '\n\tAdd tags: {}'.format(joiner.join(needed['tags']))
        if 'description_strings' in needed:
            content += '\n\tAdd to your description: {}'.format(joiner.join(needed['description_strings']))
        if 'title_strings' in needed:
            content += '\n\tAdd to your title: {}'.format(joiner.join(needed['title_strings']))
        if 'type' in needed:
            content += '\n\tChange your type: {}'.format(needed['type'])
        if 'access' in needed:
            content += '\n\tChange your access: {}'.format(needed['access'])
        if 'SR' in needed:
            content += '\n\tChange your spatial reference: {}'.format(needed['SR'])
        
        needed_ctr += 1
        if needed_ctr < len(needed_for_template):
            content += '\n\nOR\n'

    message.set_content(content)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(email_config['smtp_server'], port, context=context) as server:
        server.send_message(message)


if __name__ == '__main__':
    app.run(ssl_context='adhoc', host='0.0.0.0', port=5000)
