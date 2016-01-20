# Django RESTshop
A neat Django app that adds e-commerce functionality to any project using REST endpoints. 

Currently a work in progress. 

Requirements:

- Django >= 1.9
- PostgreSQL >= 9.4

because I really like the JSONField.

## Philosophy
An e-commerce app that can be used from existing webpage projects or mobile apps. Most e-commerce projects for Django are complete websites with templates and all. The code base is also A LOT smaller and thus easier to modify than for full webshop sites.

RESTshop is focused on supporting a product catalogue and the payment flow. 

The database model is somewhat unusual compared to the common Order->Payment setup. This is a result of many years of e-commerce development that has led me to realize that that doesn't map well to the reality of payment flows.

Design tries to follow Django and django-restframework conventions and to rely on supplied functionality as far as possible.

## API
The goal is to make the API feel RESTfully resource-oriented, e g:

- List Products `GET /products/`
- Create an Order (also cart) `POST /order/`
- Get the current order `GET /order/`
- Add OrderItems `POST /order/items/`
- Remove Order item `DELETE /order/items/1/`
- Pay through the creation of an Invoice resource. `POST /order/invoices/`

## Integrating
The Order model has a `custom` JSONField where you can stuff any extra data you need for your sales. Validate the input by connecting to the `validate_custom_order_field` signal.

Connect any code you like to the `order_paid` signal to implement your delivery functionality.

## Payment Providers
Included so far is one-off support for Stripe. Payment providers are added as regular Django apps.


## ToDo list
- Discounts
- Multiple currencies
- Real documentation!
