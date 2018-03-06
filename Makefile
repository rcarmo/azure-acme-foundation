# Set environment variables (if they're not defined yet)
export TIMESTAMP=$(shell date "+%Y-%m-%d-%H-%M-%S")
export SPEC_FILE?=project.yaml
export LOCATION?=$(shell grep location $(SPEC_FILE) | cut -d \  -f 2)
export TENANT_NAME?=$(shell grep tenant $(SPEC_FILE) | cut -d\  -f 2)


# dump environment
dump:
	set

# Generate SSH keys
keys:
	mkdir keys
	ssh-keygen -b 2048 -t rsa -f keys/$(SSH_USER) -q -N ""
	mv keys/$(SSH_USER) keys/$(SSH_USER).pem

check-vm-sizes:
	az vm list-skus --location=$(LOCATION)

check-quotas:
	az vm list-usage --location=$(LOCATION)

check-images:
	az vm image list

# Generate the Azure Resource Template parameter files
templates: $(SPEC_FILE)
	python generate.py $(SPEC_FILE)


list:
	az vm list \
	--show-details \
	--query '[].{name:name, resourceGroup:resourceGroup, location:location, powerstate:powerState, size:hardwareProfile.vmSize}'

stop-%:
	az vm deallocate \
	--ids $$(az vm list --resource-group $(TENANT_NAME)-$* --query '[].id' --output tsv) \
	--no-wait


destroy-%:
	-az group delete \
		--name $(TENANT_NAME)-$* \
		--no-wait --yes


validate-%:
	az group deployment validate \
		--resource-group $(TENANT_NAME)-$* \
		--template-file templates/$(TENANT_NAME)-$*.json


# deploy generic layers
deploy-%:
	-az group create --name $(TENANT_NAME)-$* \
		--location $(LOCATION) --output table 
	az group deployment create \
		--resource-group $(TENANT_NAME)-$* \
		--template-file templates/$(TENANT_NAME)-$*.json \
		--name cli-$(LOCATION)-$(TIMESTAMP) \
		--output table

clean:
	rm -f templates/*.json


ssh: # test invocation that doesn't validate host keys (for quick iteration)
	ssh-add keys/$(SSH_USER).pem
	ssh -A -i keys/$(SSH_USER).pem \
		-o StrictHostKeyChecking=no \
		-o UserKnownHostsFile=/dev/null \
		$(SSH_USER)@$$(az network public-ip list --query '[].{dnsSettings:dnsSettings.fqdn}' --resource-group $(TENANT_NAME)-foundation --output tsv)


endpoints:
	az network public-ip list \
		--resource-group $(TENANT_NAME)-networking \
		--query '[].{dnsSettings:dnsSettings.fqdn}' \
		--output tsv