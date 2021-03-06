import torch
import torch.optim as optim
import utils.policy as policy

import random

from utils.ngd_opt import NGDOptim, callback_with_logits

import config

class BrainOptimizer:
    def __init__(self, brain, desc):
        self.bellman = desc.bellman
        self.natural = desc.natural
        self.brain = brain

        print("BRAIN OPTIM : ", brain.mp)
        if self.natural:
            self.actor_optimizer = NGDOptim(
                brain.ac_explorer.actor_parameters(), lr=desc.lr_actor, momentum=.7, nesterov=True)
        else:
            self.actor_optimizer = optim.AdamW(
#            self.actor_optimizer = optim.SGD(#
#            self.actor_optimizer = optim.RMSprop(
                brain.ac_explorer.actor_parameters(), lr=desc.lr_actor, weight_decay=config.WD, eps=1e-5)

#        limit = config.HRL_HIGH_STEP * desc.sync_delta_a * config.TOTAL_ROUNDS // (desc.learning_delay // config.HRL_HIGH_STEP)
#        frac = lambda epoch: (1. - (epoch - 1.) / limit) if epoch < limit else 1e-2
#        self.lr = optim.lr_scheduler.LambdaLR(self.actor_optimizer, frac)

        self.steps = 0

        self.clip = desc.ppo_eps is not None
        if not self.clip:
            self.loss = policy.DDPGLoss(advantages=True, boost=False)
        else:
            self.loss = policy.PPOLoss(eps=desc.ppo_eps, advantages=True, boost=False)

    def __call__(self, qa, td_targets, w_is, probs, actions, dist, _eval, retain_graph):
        assert self.bellman or self.clip, "ppo can be only active when clipped ( in our implementation )!"

#        if self.steps > 1:
#            self.lr.step()
        self.steps += 1

        if not self.clip:#vanilla ddpg
#            if 0 == random.randint(0, 50): print("VANILA DDPG")
            pi_loss = self.loss(qa, td_targets, None, None)
        elif self.bellman:#DDPG with clip
            pi_loss = self.loss(td_targets, qa,
                dist.log_prob(actions).mean(1).detach(), probs)
        else:#PPO
#            if 0 == random.randint(0, 50): print("PPO")
            pi_loss = self.loss(qa.detach(), td_targets.detach(),
#                probs.mean(1), dist.log_prob(actions).mean(1))
                probs, dist.log_prob(actions).mean(1))
        # descent
        pi_loss = -(pi_loss * (w_is if w_is is not None else 1.)).mean()

        # learn!
#        self.brain.backprop(
#                self.actor_optimizer,
#                pi_loss,
#                self.brain.ac_explorer.actor_parameters(),
#                # next is for natural gradient experimenting!
#                None if not self.natural else callback_with_logits(self.actor_optimizer, dist, _eval),
#                just_grads=False,
#                retain_graph=retain_graph or self.natural)

        #print("\n ---> ", self.steps, self.actor_optimizer.param_groups[0]["lr"])

        return pi_loss, self.actor_optimizer
