export LD_LIBRARY_PATH="/opt/libjpeg-turbo/lib64:/opt/libjpeg-turbo/lib:${LD_LIBRARY_PATH-}"
export GENMANIP_RESULT_DIR=./evaluation/genmanip
export HF_HOME=/your/hf_home
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

python inference.py --ckpt_path ./checkpoints/EBench-Generalist-InternVLA-A1 --worker_ids 0