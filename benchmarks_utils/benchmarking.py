import aiohttp
import asyncio
import time
from pathlib import Path
import datetime
from benchmarks_utils.random_actors_names import generate_random_name

def get_public_ip(ec2, instance_id):
    response = ec2.describe_instances(InstanceIds=[instance_id])
    public_ip = response['Reservations'][0]['Instances'][0].get('PublicIpAddress')
    
    if public_ip:
        return public_ip
    else:
        raise ValueError(f"No public IP address found for instance {instance_id}")

# Function to send requests to a specific endpoint
async def call_get_http(session, public_ip_adress, call_path):
    headers = {'content-type': 'application/json'}
    try:
        async with session.get(public_ip_adress + "/" + call_path, headers=headers) as response:
            status_code = response.status
            response_json = await response.json()
            return status_code, response_json, datetime.datetime.now(datetime.timezone.utc)
    except Exception as e:
        print("error:", e)
        return None, str(e), datetime.datetime.now(datetime.timezone.utc)
    

# Function to send requests to a specific endpoint
async def call_post_http(session, public_ip_adress, call_path, args:dict):
    headers = {'content-type': 'application/json'}
    try:
        async with session.post(public_ip_adress + "/" + call_path, params=args, headers=headers) as response:
            status_code = response.status
            response_json = await response.json()
            return status_code, response_json
    except Exception as e:
        print("error:", e)
        return None, str(e)
    
async def call_write_actor(session, public_ip_adress, call_path):
    first_name, last_name = generate_random_name()
    args = {
        "first_name": first_name,
        "last_name": last_name
    }
    status_code, response_json = await call_post_http(session, public_ip_adress, call_path, args)
    return status_code, response_json, datetime.datetime.now(datetime.timezone.utc)

# Function to benchmark the cluster
async def benchmark_read_cluster(benchmark_path:Path, gate_keeper_url, num_requests=1000):
    print("Benchmarking read cluster...")
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = [call_get_http(session, gate_keeper_url, "read") for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
    
    # Write results to file
    results_file = benchmark_path / "read_results.txt"
    with open(results_file, 'a') as f:
        for status_code, response, timestamp in results:
            f.write(f"{timestamp},{status_code},{response}\n")
    
    end_time = time.time()
    total_time = end_time - start_time
    print(f"\nTotal time taken: {total_time:.2f} seconds")
    print(f"Average time per request: {total_time / num_requests:.4f} seconds")

# Function to benchmark the cluster
async def benchmark_write_cluster(benchmark_path:Path, gate_keeper_url, num_requests=1000):
    print("Benchmarking write cluster...")
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = [call_write_actor(session, gate_keeper_url, "write") for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
    # Write results to file
    results_file = benchmark_path / "write_results.txt"
    with open(results_file, 'a') as f:
        for status_code, response, timestamp in results:
            f.write(f"{timestamp},{status_code},{response}\n")
    
    end_time = time.time()
    total_time = end_time - start_time
    print(f"\nTotal time taken: {total_time:.4f} seconds")
    print(f"Average time per request: {total_time / num_requests:.4f} seconds")

async def switch_proxy_mode(gate_keeper_url, mode = 0):
    args = {
        "mode": mode
    }
    async with aiohttp.ClientSession() as session:
        await call_post_http(session, gate_keeper_url, "mode", args)
        print(f"Switched to mode {mode}")

async def benchmarks_cluster(benchmark_path:Path, gate_keeper_ip, num_requests=1000, wait_time_between_mode_s = 60):
    gate_keeper_url = f"http://{gate_keeper_ip}:80"
    assert(benchmark_path.exists(), f"Benchmark path {benchmark_path} does not exist")
    assert(benchmark_path.is_dir(), f"Benchmark path {benchmark_path} is not a directory")
    try:
        print("Waiting initially to not have any metrics from the installation")
        time.sleep(2*wait_time_between_mode_s)
        print("****************************************")
        time.sleep(wait_time_between_mode_s)
        await asyncio.gather(
            #benchmark_write_cluster(gate_keeper_url, num_requests),
            benchmark_read_cluster(gate_keeper_url, num_requests)
        )
        print("Waiting after read/write requests mode 0...")
        print("****************************************")
        time.sleep(wait_time_between_mode_s)
        await switch_proxy_mode(gate_keeper_url, 1)
        await asyncio.gather(
            #benchmark_write_cluster(gate_keeper_url, num_requests),
            benchmark_read_cluster(gate_keeper_url, num_requests)
        )
        print("Waiting after read/write requests mode 1...")
        print("****************************************")
        time.sleep(wait_time_between_mode_s)
        await switch_proxy_mode(gate_keeper_url, 2)
        await asyncio.gather(
            #benchmark_write_cluster(gate_keeper_url, num_requests),
            benchmark_read_cluster(gate_keeper_url, num_requests)
        )
        print("Waiting after read/write requests mode 2...")
        time.sleep(wait_time_between_mode_s)
        print("****************************************")
    except Exception as e:
        print(f"Error : {e}")

