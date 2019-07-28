#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError
import argparse
from time import sleep


class Ec2Manager:
    def __init__(self, instance_id):
        self.ec2 = boto3.client('ec2')
        self.instance_id = instance_id

    # 'pending'|'running'|'shutting-down'|'terminated'|'stopping'|'stopped'
    def _waiting_for(self, end_status, max_times=6):
        times = max_times
        status = ""
        while status != end_status and times > 0:
            sleep(10)
            times = times -1
            status = self.status()
            print("current status is {}. waiting to {}".format(status, end_status))
        return status == end_status

    def start(self):
        status = self.status()
        if status != 'stopped':
            print("The status of  the instance {} is {}. Cannot start an {} instance".format(self.instance_id,
                                                                                             status,
                                                                                             status))
            return False
        print("Starting the instance {}".format(self.instance_id))
        ret = self.ec2.start_instances(InstanceIds=[self.instance_id])
        return self._waiting_for('running')

    def stop(self):
        status = self.status()
        if status not in ("running"):
            print("The status of the instance {} is {}. Cannot stop an {} instance".format(self.instance_id,
                                                                                           status,
                                                                                           status))
            return False
        print("Instance {} is currently {}".format(self.instance_id, status))
        ret = self.ec2.stop_instances(InstanceIds=[self.instance_id])
        return self._waiting_for('stopped')

    def public_ip(self):
        ret = {}
        try:
            ret = self.ec2.describe_instances(InstanceIds=[self.instance_id])
            try:
                return ret['Reservations'][0]['Instances'][0]['NetworkInterfaces'][0]['Association'].get('PublicIp', 'None')
            except KeyError:
                return "None"

        except ClientError as error:
            print(error)
            return "not exists"

    def status(self):
        ret = {}
        try:
            ret = self.ec2.describe_instance_status(InstanceIds=[self.instance_id], IncludeAllInstances=True)
            return ret['InstanceStatuses'][0]['InstanceState']['Name']
        except ClientError as error:
            print(error)
            return "not exists"

    def action(self, verb):
        if verb == 'START':
            ret =  self.start()
            print("Current IP is {}".format(self.public_ip()))
            return ret
        if verb == 'STOP':
            return self.stop()
        if verb == 'STATUS':
            status = self.status()
            print("The status of the instance {} is {}. Current IP {}".format(self.instance_id, status, self.public_ip()))
            return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="This program starts/stops/view a instance")
    parser.add_argument("id", help="The instance id")
    parser.add_argument("verb",
                        help="action to do: START|STOP|STATUS",
                        default="START",
                        choices=["START", "STOP", "STATUS"])
    parser.add_argument("--profile", help="AWS Profile to use")

    args = parser.parse_args()
    if args.profile:
        print("working with the profile: {}".format(args.profile))
        boto3.setup_default_session(profile_name=args.profile)

    sm = Ec2Manager(instance_id=args.id)
    print(sm.action(args.verb))

