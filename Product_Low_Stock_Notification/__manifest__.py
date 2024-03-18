{
    'name': 'Product Low Stock Notification',
    "summary":"Notify User Low Stock Product",
    'author':'Petra Software',
    'company': 'Petra Software',
    'maintainer': 'Petra Software',
    'website':'www.t-petra.com',
     'license': 'LGPL-3',
    "depends":['base','stock'],
    "data":[
        "data/Send_Mails.xml",
        "views/low_stock_notification.xml",
        "views/Notify_user.xml",
        "views/Product_stock_notification.xml",
        "views/Min_Qty.xml",
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
     'images': ['static/description/banner.png'],
    'price':10,
    'currency':'USD'
}
