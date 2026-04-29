#!/bin/bash

# ========================= setting =========================
GENMANIP_PATH="/your/path/to/GenManip-Sim" 
NUM_CLIENTS=1 #num of eval clients
RUN_ID="your run id" 
POLICY_CFG="pi05_ebench_all" #TrainConfig.name of your model 
POLICY_PATH="your/path/to/checkpoints"
Horizon=30 #replan horizon
TOKEN="your token"
URL="the end point"

echo "==============Eval info =============="
echo "policy_cfg: $POLICY_CFG"
echo "policy_path: $POLICY_PATH"
echo "replan horizon: $Horizon"
echo "run_id: $RUN_ID"

# ========================= Start Model Server =========================
echo "Starting model server..."

cd <your/path/to/openpi>
source </your/path/to/openpi/.venv/bin/activate>

MODEL_PIDS=()
for ((i=0; i<NUM_CLIENTS; i++)); do
    export CUDA_VISIBLE_DEVICES=$(($i / 2)) #set CUDA_VISIBLE_DEVICES for each model server based on your GPU size
    PORT=$((8000 + 2*i))
    python scripts/serve_policy.py --port $PORT  policy:checkpoint --policy.config=$POLICY_CFG  --policy.dir=$POLICY_PATH &
    MODEL_PIDS+=($!)
done

deactivate 

sleep 60

# ========================= Start GenManip-Client =========================
echo "start eval client..."
conda activate <your env of GenManip-client>


CLIENT_PIDS=()
for ((i=0; i<NUM_CLIENTS; i++)); do
    python scripts/pi_eval_client_online.py  --horizon $Horizon --model_host 0.0.0.0 --model_port $((8000 + 2*i)) --worker_ids "$i" --run_id "$RUN_ID" --token $TOKEN  --eval_host $URL &
    CLIENT_PIDS+=($!)
done


wait "${CLIENT_PIDS[@]}"

# kill model server
for pid in "${MODEL_PIDS[@]}"; do
    kill $pid
done

sleep 25