import json
import re

import http.cookiejar
from urllib.request import Request, build_opener
import urllib
from urllib import parse
from http.cookiejar import CookieJar

from flask import Flask, render_template, request, make_response, jsonify, send_from_directory

from fpdf import FPDF
from PIL import Image, ImageChops

import os

application = Flask(__name__)

agentheaders={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}

@application.route('/')
def render_index():
    return render_template('index.html')

def convert_images_to_pdf(image_array, opener_ref, init_h):
    h = init_h.copy()
    pdf_set = False
    pdf = None
    for index, r in enumerate(image_array):
        img_req = Request(r, data=None, headers=h)
        img_resp = opener_ref.open(img_req)
        if img_resp:
            file_type = img_resp.headers['Content-Type'].split(';')[0].lower().split("/")[1]
            file_path = '/tmp/' + str(index) + '.' + file_type
            with open(file_path, 'wb') as f:
                f.write(img_resp.read())
                f.close()
                try:
                    im = Image.open(file_path)
                    if not pdf_set:
                        pdf = FPDF("L","pt",[im.size[1],im.size[0]])
                        pdf.set_margins(0,0,0)
                        pdf_set = True
                    pdf.add_page()
                    pdf.image(file_path, 0, 0)
                except:
                    pass
            if os.path.isfile(file_path):
                os.remove(file_path)
    resp_file = pdf.output('/tmp/pdf_output.pdf', 'F')
    return resp_file

def update_cookie(header, cookie_jar):
    header_copy = header.copy()
    cookie_refs = []
    for c in cookie_jar:
        cookie_name, cookie_val = str(c.__dict__.get('name')), str(c.__dict__.get('value'))
        cookie_refs.append( cookie_name + "=" + cookie_val )
    if cookie_refs:
        header_copy['Cookie'] = "; ".join(cookie_refs)
    return header_copy
    

@application.route('/now/<file_id>', methods=['GET', 'POST'])
def download_pdf(file_id):
    # retrieve email and password
    content = request.get_json(force=True) or {}
    email = content.get('email') or 'dummy@nowhere.com'
    password = content.get('password') or 'notvalidpassword'

    error_msg = "unknown error"

    try:
        # set basic cookies
        cookie_request = Request("https://docsend.com/view/" + file_id, data=None, headers=agentheaders)
        cj = CookieJar()
        op = build_opener(urllib.request.HTTPCookieProcessor(cj))
        cookie_resp = op.open(cookie_request)
        image_array_body = ""
        if cookie_resp:
            auth_result = cookie_resp.read()

            decoded = auth_result.decode()

            auth_matches = re.search(r'link_auth_form\[passcode\]', decoded)
            auth_matches_email = re.search(r'link_auth_form\[email\]', decoded)
            if auth_matches:
                auth_token_match = re.search(r'authenticity_token\"\s*value\=\"(.*)\"', decoded)
                if auth_token_match:
                    auth_token = auth_token_match[1]
                    # password required
                    # try given password
                    if password:
                        data_send = parse.urlencode({"_method": "patch", "authenticity_token": auth_token, 'commit': "Continue", "link_auth_form[email]": email, "link_auth_form[passcode]": password}).encode("ascii")
                        auth_request = Request("https://docsend.com/view/" + file_id, data=data_send, headers=agentheaders)
                        h = agentheaders.copy()
                        h = update_cookie(h, cj)
                        
                        auth_request = Request("https://docsend.com/view/" + file_id, data=data_send, headers=h)
                        auth_result = op.open(auth_request)
                        if auth_result:
                            auth_body = auth_result.read()
                            incorrect_email = re.search(r'class\=\"error\"\>Passcode', auth_body.decode())
                            if incorrect_email:
                                return jsonify({"error": 'password invalid'}), 401
                            image_array_body = auth_body

            elif auth_matches_email:
                auth_token_match = re.search(r'authenticity_token\"\s*value\=\"(.*)\"', decoded)
                if auth_token_match:
                    auth_token = auth_token_match[1]
                    data_send = parse.urlencode({"_method": "patch", "authenticity_token": auth_token, 'commit': "Continue", "link_auth_form[email]": email}).encode("ascii")
                    auth_request = Request("https://docsend.com/view/" + file_id, data=data_send, headers=agentheaders)
                    h = agentheaders.copy()
                    h = update_cookie(h, cj)

                    auth_request = Request("https://docsend.com/view/" + file_id, data=data_send, headers=h)
                    auth_result = op.open(auth_request)
                    if auth_result:
                        image_array_body = auth_result.read()
            else:
                image_array_body = cookie_resp.read()

        data_matches = re.findall(r'data\-url\=\'(https\:\/\/docsend.com\/view\/.*\/thumb\/\d+)\'', image_array_body.decode())
        if data_matches:
            data_matches = [thumb.replace('thumb', 'page_data') for thumb in data_matches]

        results = []

        h = None
        for index, d in enumerate(data_matches):
            if index >= 0:
                h = agentheaders.copy()
                h = update_cookie(h, cj)

            req = Request(d, data=None, headers=h)
            try:
                req_resp = op.open(req)
            except Exception as e:
                return jsonify({"error": 'password invalid'}), 401
            if req_resp:
                tada = req_resp.read()
                tada_json = json.loads(tada)
                results.append(tada_json.get('imageUrl'))

        if results:
            pdf_file = convert_images_to_pdf(results, op, h)
            return send_from_directory('/tmp/', 'pdf_output.pdf')

    except Exception as e:
        error_msg = str(e)

    return jsonify({"error": error_msg}), 401

if __name__ == "__main__":
    application.run(host='0.0.0.0', debug=True, threaded=True)
