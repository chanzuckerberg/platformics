"""
Helpers for writing Jinja2 templates based on LinkML schema objects.

The wrapper classes in this module are entirely centered around providing convenience
functions to keep complicated LinkML-specific logic out of our Jinja2 templates.
"""

from functools import cached_property

import strcase
from linkml_runtime.linkml_model.meta import ClassDefinition, EnumDefinition, SlotDefinition
from linkml_runtime.utils.schemaview import SchemaView


class FieldWrapper:
    """
    Convenience functions for LinkML slots
    """

    def __init__(self, view: SchemaView, wrapped_field: SlotDefinition):
        self.view = view
        self.wrapped_field = wrapped_field

    def __getattr__(self, attr: str) -> str:
        """
        Error if a property doesn't exist
        """
        raise NotImplementedError(f"please define field property {attr}")

    @cached_property
    def identifier(self) -> str:
        return self.wrapped_field.identifier

    @cached_property
    def name(self) -> str:
        return self.wrapped_field.name

    @cached_property
    def multivalued(self) -> str:
        return self.wrapped_field.multivalued

    @cached_property
    def required(self) -> str:
        return self.wrapped_field.required

    @cached_property
    def type(self) -> str:
        return self.wrapped_field.range

    @cached_property
    def inverse(self) -> str:
        return self.wrapped_field.inverse

    @cached_property
    def inverse_class(self) -> str:
        return self.wrapped_field.inverse.split(".")[0]

    @cached_property
    def inverse_class_snake_name(self) -> str:
        return strcase.to_snake(self.inverse_class)

    @cached_property
    def inverse_field(self) -> str:
        return self.wrapped_field.inverse.split(".")[1]

    @cached_property
    def is_enum(self) -> bool:
        field = self.view.get_element(self.wrapped_field.range)
        if isinstance(field, EnumDefinition):
            return True
        return False

    @cached_property
    def is_entity(self) -> bool:
        field = self.view.get_element(self.wrapped_field.range)
        if isinstance(field, ClassDefinition):
            return True
        return False

    @property
    def related_class(self) -> "EntityWrapper":
        return EntityWrapper(self.view, self.view.get_element(self.wrapped_field.range))

    @property
    def related_enum(self) -> "EnumWrapper":
        return EnumWrapper(self.view, self.view.get_element(self.wrapped_field.range))

    @property
    def factory_type(self) -> str:
        return (
            self.wrapped_field.annotations["factory_type"].value
            if self.wrapped_field.annotations and self.wrapped_field.annotations["factory_type"]
            else None
        )


class EnumWrapper:
    """
    Convenience functions for LinkML enums
    """

    def __init__(self, view: SchemaView, wrapped_class: EnumDefinition):
        self.view = view
        self.wrapped_class = wrapped_class

    # Blow up if a property doesn't exist
    def __getattr__(self, attr: str) -> str:
        raise NotImplementedError(f"please define enum property {attr}")

    @cached_property
    def name(self) -> str:
        return self.wrapped_class.name

    @cached_property
    def permissible_values(self) -> str:
        return self.wrapped_class.permissible_values


class EntityWrapper:
    """
    Convenience functions for LinkML entities
    """

    def __init__(self, view: SchemaView, wrapped_class: ClassDefinition):
        self.view = view
        self.wrapped_class = wrapped_class

    # Blow up if a property doesn't exist
    def __getattr__(self, attr: str) -> str:
        raise NotImplementedError(f"please define entity property {attr}")

    @cached_property
    def name(self) -> str:
        return self.wrapped_class.name

    @cached_property
    def plural_camel_name(self) -> str:
        return self.wrapped_class.annotations["plural"].value

    @cached_property
    def plural_snake_name(self) -> str:
        return strcase.to_snake(self.plural_camel_name)

    @cached_property
    def camel_name(self) -> str:
        return self.wrapped_class.name

    @cached_property
    def snake_name(self) -> str:
        return strcase.to_snake(self.name)

    @cached_property
    def writable_fields(self) -> list[FieldWrapper]:
        return [FieldWrapper(self.view, item) for item in self.view.class_induced_slots(self.name) if not item.readonly]

    @cached_property
    def identifier(self) -> str:
        # Prioritize sending back identifiers from the entity mixin instead of inherited fields.
        for field in self.all_fields:
            # FIXME, the entity.id / entity_id relationship is a little brittle right now :(
            if field.identifier:
                if "EntityMixin" in field.wrapped_field.domain_of:
                    return field.name
        for field in self.all_fields:
            if field.identifier:
                return field.name
        raise Exception("No identifier found")

    @cached_property
    def readable_fields(self) -> list[FieldWrapper]:
        return [FieldWrapper(self.view, item) for item in self.view.class_induced_slots(self.name)]

    @cached_property
    def all_fields(self) -> list[FieldWrapper]:
        return [FieldWrapper(self.view, item) for item in self.view.class_induced_slots(self.name)]

    @cached_property
    def owned_fields(self) -> list[FieldWrapper]:
        return [
            FieldWrapper(self.view, item)
            for item in self.view.class_induced_slots(self.name)
            if "Entity" not in item.domain_of
        ]

    @cached_property
    def enum_fields(self) -> list[FieldWrapper]:
        enumfields = self.view.all_enums()
        class_names = [k for k, _ in enumfields.items()]
        return [field for field in self.all_fields if field.type in class_names]

    @cached_property
    def related_fields(self) -> list[FieldWrapper]:
        return [field for field in self.all_fields if field.is_entity]


class ViewWrapper:
    """
    Convenience functions for LinkML schema views
    """

    def __init__(self, view: SchemaView):
        self.view = view

    # Blow up if a property doesn't exist
    def __getattr__(self, attr: str) -> str:
        raise NotImplementedError(f"please define view property {attr}")

    @cached_property
    def enums(self) -> list[EnumWrapper]:
        enums = []
        for enum_name in self.view.all_enums():
            enum = self.view.get_element(enum_name)
            enums.append(EnumWrapper(self.view, enum))
        return enums

    @cached_property
    def entities(self) -> list[EntityWrapper]:
        classes = []
        for class_name in self.view.all_classes():
            cls = self.view.get_element(class_name)
            if cls.mixin:
                continue
            # If this class doesn't descend from Entity, skip it.
            if cls.is_a != "Entity":
                continue
            classes.append(EntityWrapper(self.view, cls))
        return classes
