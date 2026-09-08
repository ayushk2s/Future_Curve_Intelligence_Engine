# Futures Curve Intelligence Engine
.DEFAULT_GOAL := help
PY ?= python3

help:  ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup:  ## install dependencies
	$(PY) -m pip install -r requirements.txt

gold:  ## run the gold pipeline (fetch -> ... -> backtest)
	$(PY) src/pipeline.py

gold-fast:  ## gold pipeline, reuse cached raw data
	$(PY) src/pipeline.py --skip-fetch

crypto:  ## run the BTC + ETH pipeline (Deribit, no key)
	$(PY) src/crypto_pipeline.py

crypto-fast:  ## crypto pipeline, reuse cached raw data
	$(PY) src/crypto_pipeline.py --skip-fetch

demo:  ## run everything and print the headline results table
	$(PY) demo.py

dashboard:  ## launch the Streamlit dashboard
	$(PY) -m streamlit run app/dashboard.py

monitor:  ## print the gold deviation-alert digest
	$(PY) src/monitor.py --no-refresh

test:  ## run the test suite
	$(PY) -m pytest -q tests/

pdf:  ## regenerate docs/EXPLAINER.pdf from docs/explainer.html (needs Google Chrome)
	"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
	  --no-pdf-header-footer --print-to-pdf=docs/EXPLAINER.pdf docs/explainer.html

clean:  ## delete generated data (keeps raw)
	rm -rf data/clean data/output data/crypto/*/clean data/crypto/*/output

.PHONY: help setup gold gold-fast crypto crypto-fast demo dashboard monitor test pdf clean
