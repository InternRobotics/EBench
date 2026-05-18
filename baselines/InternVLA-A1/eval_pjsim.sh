export LD_LIBRARY_PATH="/opt/libjpeg-turbo/lib64:/opt/libjpeg-turbo/lib:${LD_LIBRARY_PATH-}"
export GENMANIP_RESULT_DIR=./client_results
export HF_HOME=./hf_home
export HF_HUB_OFFLINE=0
export TRANSFORMERS_OFFLINE=0

python inference.py --ckpt_path your/path/to/checkpoints/EBench-Generalist-InternVLA-A1 --worker_ids 0