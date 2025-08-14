from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from django.db.models.signals import post_delete
from django.dispatch import receiver
from products.models import Product


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

    def get_id(self, obj):
        return str(obj.pk)
    
@receiver(post_delete, sender=Product)
def delete_product_from_index(sender, instance, **kwargs):
    registry.delete(instance)