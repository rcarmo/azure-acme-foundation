# Set environment variables (if they're not defined yet)
export TENANT_NAME?=contoso
export LOCATION?=eastus
export SSH_USER?=azureuser
export TIMESTAMP=`date "+%Y-%m-%d-%H-%M-%S"`

# Generate SSH keys
keys:
	mkdir keys
	ssh-keygen -b 2048 -t rsa -f keys/$(SSH_USER) -q -N ""
	mv keys/$(SSH_USER) keys/$(SSH_USER).pem


# Generate the Azure Resource Template parameter files
params:
	-mkdir parameters
	python genparams.py


destroy-%:
	-az group delete \
		--name $(TENANT_NAME)-$* \
		--no-wait --yes


validate-%:
	az group deployment validate \
		--resource-group $(TENANT_NAME)-$* 
		--template-file templates/$*.json \
		--parameters @parameters/$*.json


deploy-foundation:
	-az group create --name $(TENANT_NAME)-foundation \
		--location $(LOCATION) --output table 
	az group deployment create \
		--resource-group $(TENANT_NAME)-foundation \
		--template-file templates/foundation.json \
		--parameters @parameters/foundation.json \
		--name cli-$(LOCATION)-$(TIMESTAMP) \
		--output table

# deploy generic layers
deploy-%:
	-az group create --name $(TENANT_NAME)-$* \
		--location $(LOCATION) --output table 
	az group deployment create \
		--resource-group $(TENANT_NAME)-$* \
		--template-file templates/generic-layer.json \
		--parameters @parameters/$*.json \
		--name cli-$(LOCATION)-$(TIMESTAMP) \
		--output table


clean:
	rm -rf parameters


ssh: # test invocation that doesn't validate host keys (for quick iteration)
	ssh-add keys/$(SSH_USER).pem
	ssh -A -i keys/$(SSH_USER).pem \
		-o StrictHostKeyChecking=no \
		-o UserKnownHostsFile=/dev/null \
		$(SSH_USER)@$$(az network public-ip list --query '[].{dnsSettings:dnsSettings.fqdn}' --resource-group $(TENANT_NAME)-foundation --output tsv)


endpoints:
	az network public-ip list \
		--resource-group $(TENANT_NAME)-foundation \
		--query '[].{dnsSettings:dnsSettings.fqdn}' \
		--output tsv