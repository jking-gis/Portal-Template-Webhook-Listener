# Portal-Template-Webhook-Listener
A webhook listener that allows you to define a template for various items within your portal. When a new or updated item is mismatched with the template, an email is sent out to a configured group of people.

# Deployment Steps
## App Configuration
* To edit the settings for the email and SMTP server, edit emailConfig.json
* To enter credential information for the portal, so your app can run, enter it into appCredentials.json
* To define templates for your portal items, so that they match, add/remove/edit items within itemTemplates.json

## Python Environment Setup
* Make sure that you use python 3.X as your python environment for this flask server
* Make sure the following packages are installed into your python environment (use conda install <package-name>, for conda environments)
  * flask
  * flask-cors
  * arcgis
  
## Run ListeningServer.py

## Portal Setup
* Navigate to your Portal's rest directory
* Follow the steps here: https://enterprise.arcgis.com/en/portal/latest/administer/windows/create-and-manage-webhooks.htm
* When you actually create the webhook:
  * Name the webhook whatever
  * Enter the URL to your flask server in the payload URL
  * Make the webhook trigger on any event

## Try creating or editing Portal items, and you should receive an email if the item mismatches your templates in itemTemplates.json
