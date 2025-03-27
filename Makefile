#### YUMI_SYNC
####
#### This File is distributed under GPLv3
####

#### Self-Documenting Makefile
#### This is based on https://gellardo.github.io/blog/posts/2021-06-10-self-documenting-makefile/


.DEFAULT_GOAL := help
.PHONY: help


install: ## Install YUMI_SYNC (needs leading sudo)
	sudo bash -x scripts/install.sh


uninstall: ## Uninstall YUMI_SYNC
	@bash -c 'scripts/uninstall.sh'

rebuildvenv: ## Rebuild virtual environment
	@bash -c 'scripts/install.sh -r'

update: ## Fetch latest changes
	@git fetch && git pull

help: ## Shows this help
	@printf "YUMI_SYNC by Yumi-Lab (https://github.com/Yumi_lab)\n"
	@printf "Usage:\n\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
