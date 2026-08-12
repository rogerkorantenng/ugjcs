.PHONY: check lint typecheck test e2e
lint:
	npm run lint -- --max-warnings=0

typecheck:
	npx tsc --noEmit

test:
	npx vitest run

check: lint typecheck test

e2e:
	npx playwright test
