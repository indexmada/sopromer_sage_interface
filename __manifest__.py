# -*- coding: utf-8 -*-
{
    'name': "sopromer_sage_interface",

    'summary': """
        Rapport de Vente(excel)
        Entrée En Stock
        MaJ Article
        """,

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'base_setup', 'sale', 'point_of_sale','stock', 'pos_combo_product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/inherit_pos_session_view.xml',
        'views/import_stock_views.xml',
        'views/config_settings_view.xml',
        'views/cron.xml',
    ],
}

# Cck