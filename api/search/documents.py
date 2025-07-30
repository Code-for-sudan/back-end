from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from products.models import Product

@registry.register_document
class ProductDocument(Document):
    store_id = fields.IntegerField(attr='store.id')
    
    class Index:
        name = 'products'
        settings = {'number_of_shards': 1,'number_of_replicas': 0}

    class Django:
        model = Product
        fields = ['product_name','product_description','category']