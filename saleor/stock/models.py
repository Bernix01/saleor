from django.db import models
from django.utils.translation import pgettext_lazy

from ..core.exceptions import InsufficientStock
from ..product.models import ProductVariant
from ..shipping.models import ShippingZone
from ..warehouse.models import Warehouse


class StockQuerySet(models.QuerySet):
    def get_stock_for_country(self, product_variant: ProductVariant, country_code: str):
        shipping_zone = ShippingZone.objects.prefetch_related("warehouse_set").get(
            countries__icontains=country_code
        )
        return self.get(
            warehouse=models.Subquery(shipping_zone.warehouse_set.get()),
            product_variant=product_variant,
        )


class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, null=False, on_delete=models.PROTECT)
    product_variant = models.ForeignKey(
        ProductVariant, null=False, on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField()
    quantity_allocated = models.PositiveIntegerField()

    objects = StockQuerySet.as_manager()

    class Meta:
        unique_together = [["warehouse", "product_variant"]]
        permissions = (
            (
                "manage_stocks",
                pgettext_lazy("Permission description", "Manage stocks."),
            ),
        )

    def __str__(self):
        return f"{self.product_variant} - {self.warehouse.name}"

    @property
    def quantity_available(self) -> int:
        return max(self.quantity - self.quantity_allocated, 0)

    @property
    def is_available(self):
        return self.quantity > 0

    def check_quantity(self, quantity):
        if quantity > self.quantity_available:
            raise InsufficientStock(self)
