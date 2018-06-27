from django.template.defaulttags import register

@register.filter
def get_item(dictionary, key):
    if dictionary != None and dictionary.get(key) != None:
        return dictionary.get(key)
    else:
        return 0