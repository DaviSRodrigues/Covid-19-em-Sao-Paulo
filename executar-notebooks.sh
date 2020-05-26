#!/bin/bash
set -e

for file in *.ipynb
do
	if papermill --kernel python3 "${file}" "${file}"; then
        echo "${file} foi executado com sucesso.\n\n\n\n"
    else
        echo "Erro ao executar ${file}"
    fi
done