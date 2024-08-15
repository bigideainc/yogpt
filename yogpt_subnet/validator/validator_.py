import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
from communex.module.module import Module
from loguru import logger
import os
import warnings
from dotenv import load_dotenv

warnings.filterwarnings(
    "ignore",
    message="Detected filter using positional arguments. Prefer using the 'filter' keyword argument instead."
)

load_dotenv()

cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

if not os.path.exists(cred_path):
    raise FileNotFoundError(f"Credential file not found: {cred_path}")

cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

db = firestore.client()

class ModelRewardChecker(Module):
    def __init__(self) -> None:
        super().__init__()
        logger.info(f"model cheker initialized")
        self.model_thresholds = {
            "llama2-7b": {"threshold": 0.20, "training_per_hour": 1.2, "fine_tuning_time": (10, 12)},
            "OpenELM-270M": {"threshold": 0.50, "training_per_hour": 1.0, "fine_tuning_time": (3, 5)},
            "OpenELM-450M": {"threshold": 0.35, "training_per_hour": 1.3, "fine_tuning_time": (6, 8)},
            "OpenELM-3B": {"threshold": 0.20, "training_per_hour": 2.2, "fine_tuning_time": (10, 12)},
            "GPT2": {"threshold": 0.50, "training_per_hour": 1.5, "fine_tuning_time": (3, 5)},
            "LLama3B": {"threshold": 0.35, "training_per_hour": 2.2, "fine_tuning_time": (6, 8)}
        }

    def calculate_reward(self, job_data):
        model_tuned = job_data.get('model_tuned')
        loss = job_data.get('loss')
        duration_str = job_data.get('totalPipelineTime')
        model_created = job_data.get('huggingFaceRepoId')
        logger.info(f"tuned models extracted")
        # Check if huggingFaceRepoId is not empty and contains 'huggingface'
        if not model_created or 'huggingface' not in model_created.lower():
            return 0, "No valid Hugging Face model created"

        if model_tuned not in self.model_thresholds:
            return 0, "Model not found in thresholds"

        model_info = self.model_thresholds[model_tuned]
        threshold = model_info['threshold']
        training_per_hour = model_info['training_per_hour']
        min_time, max_time = model_info['fine_tuning_time']

        try:
            duration_parts =str(duration_str).split(':')
            if len(duration_parts) == 3:  # HH:MM:SS format
                hours, minutes, seconds = map(int, duration_parts)
                duration = hours + minutes / 60 + seconds / 3600
            elif len(duration_parts) == 2:  # HH:MM format
                hours, minutes = map(int, duration_parts)
                duration = hours + minutes / 60
            else:
                return 0, f"Invalid duration format: {duration_str}"
        except ValueError:
            return 0, f"Unable to parse duration: {duration_str}"

        if loss > threshold:
            return 0, "Loss exceeds threshold"

        if duration < min_time:
            return 0, f"Training completed too quickly. Expected minimum {min_time} hours, but took {duration:.2f} hours"

        if duration > max_time:
            return 0, f"Tr# if score_dict:
        #     self.set_weights(score_dict)
        aining took too long. Expected maximum {max_time} hours, but took {duration:.2f} hours"

        reward = training_per_hour * duration
        logger.info(f"miner reward is {reward}")
        return reward, f"Reward granted for {duration:.2f} hours of training"

    def reward_completed_jobs(self):
        logger.info(f"models data started omming in")
        # jobs_ref = db.collection('completed_jobs').where('status', '==', 'pending_reward')
        jobs_ref = db.collection('completed_jobs')

        completed_jobs = jobs_ref.stream()
        score_dict = {}
        for job in completed_jobs:
            logger.info(f"score data {score_dict}")
            job_data = job.to_dict()
            print(job_data)
            reward, message = self.calculate_reward(job_data)
            logger.info(f"{reward} {message}")
            
            if reward > 0:
                score =reward/100
                weight = self.assign_weight(score)
                score_dict[job_data['minerId']] = score
                job.reference.update({
                    'status': 'rewarded',
                    'reward': reward,
                    'reward_message': message
                })
                # self.update_miner_account(job_data['minerId'], reward)
            else:
                # Update the job status with no reward
                job.reference.update({
                    'status': 'not_rewarded',
                    'reward_message': message
                })
        if score_dict:
            self.set_weights(score_dict)
        
    def set_weights(self, score_dict: dict[int, float]) -> None:
        """
        Set weights for miners based on their scores and update the blockchain.
        """
        # Apply cutting logic to conform with subnet weight limits
        logger.info(f"received score dict{score_dict}")
        score_dict = self.cut_to_max_allowed_weights(score_dict)

        weighted_scores = {uid: self.assign_weight(score) for uid, score in score_dict.items()}
        uids = list(weighted_scores.keys())
        weights = list(weighted_scores.values())
        breakpoint()
        # Call the blockchain to vote and set weights
        self.client.vote(key=self.key, uids=uids, weights=weights, netuid=self.netuid)
    
    def cut_to_max_allowed_weights(self, score_dict: dict[int, float], max_allowed_weights: int = 420) -> dict[int, float]:
        """
        Cut the scores to the maximum allowed weights.
        """
        sorted_scores = sorted(score_dict.items(), key=lambda x: x[1], reverse=True)
        cut_scores = sorted_scores[:max_allowed_weights]
        logger.info(f"cut scores {cut_scores}")
        return dict(cut_scores)

    # def update_miner_account(self, miner_id, reward):
    #     miner_ref = db.collection('miners').document(miner_id)
        
    #     # Get the current miner data
    #     miner_data = miner_ref.get().to_dict()
        
    #     if miner_data is None:
    #         logger.error(f"Miner with ID {miner_id} not found")
    #         return
        
    #     # Check if the Account field exists
    #     if 'Account' in miner_data:
    #         # If it exists, add the reward to the current value
    #         new_balance = miner_data['Account'] + reward
    #     else:
    #         # If it doesn't exist, create it with the reward value
    #         new_balance = reward
        
    #     # Update the miner's account
    #     miner_ref.update({
    #         'Account': new_balance
    #     })
        
    #     logger.info(f"Updated miner {miner_id} account. New balance: {new_balance}")

if __name__== "__main__":
    rc  = ModelRewardChecker()
    rc.reward_completed_jobs()
