MIN_NUM = float('-inf')
MAX_NUM = float('inf')


class PID(object):
    def __init__(self, kp, ki, kd, mn=MIN_NUM, mx=MAX_NUM):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.min = mn
        self.max = mx

        self.int_val = self.last_int_val = self.last_error = 0.

    def reset(self):
        self.int_val = 0.0
        self.last_int_val = 0.0

    def step(self, error, sample_time):
        derivative = (error - self.last_error)
        self.int_val = derivative + error
        self.last_error = error

        y = self.kp * error + self.ki * self.int_val + self.kd * derivative;
        val = max(self.min, min(y, self.max))

        return val
