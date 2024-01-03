.PHONY: codegen
codegen:
	python3 platformics/cli/main.py api generate --schemafile ./schema/test_app.yaml --output-prefix .

.PHONY: clean
clean:
	rm -rf api database database_migrations cerbos

.PHONY: restart
restart:
	supervisorctl restart test_app

