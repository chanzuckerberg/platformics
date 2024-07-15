# How To: Customize codegen templates
Platformics supports replacing one codegen template with another, either globally or for a specific type.


## Use a different template by default
1. Find the template that you want to replace in the [base platformics template directory](https://github.com/chanzuckerberg/platformics/tree/main/platformics/codegen/templates)
2. Create a directory that will contain your overriden templates, such as `template_overrides`
3. Copy that template to your overrides directory with the same path relative to `templates` in the platformics repo. For example, if you want to override `platformics/codegen/templates/database/models/class_name.py.j2`, copy it to `template_overrides/database/models/class_name.py.j2`
4. Modify the template as much as you want
5. When you run codegen, include the overrides folder as a parameter to the codegen tool. For example, update the `codegen` target in the `Makefile` for your project directory to look like: 
   ```
   	$(docker_compose_run) $(APP_CONTAINER) platformics api generate --schemafile ./schema/schema.yaml --template-override-paths template_overrides --output-prefix .
   ```

## Use a different template for a specific class
1. Find the template that you want to replace in the [base platformics template directory](https://github.com/chanzuckerberg/platformics/tree/main/platformics/codegen/templates). Note that this **only works for files named `class_name.*`**!
2. Create a directory that will contain your overriden templates, such as `template_overrides`
3. Copy that template to your overrides directory with the same path relative to `templates` in the platformics repo, but the **filename needs to reflect the camel_case class name**. For example, if you want to override `platformics/codegen/templates/database/models/class_name.py.j2`, for a class called `MyData`, copy it to `template_overrides/database/models/my_data.py.j2`
4. Modify the template as much as you want
5. When you run codegen, include the overrides folder as a parameter to the codegen tool. For example, update the `codegen` target in the `Makefile` for your project directory to look like: 
   ```
   	$(docker_compose_run) $(APP_CONTAINER) platformics api generate --schemafile ./schema/schema.yaml --template-override-paths template_overrides --output-prefix .
   ```
