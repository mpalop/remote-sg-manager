#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError
import argparse
import json
import urllib.request


def current_ip():
    ip = json.loads(urllib.request.urlopen('https://httpbin.org/ip').read())
    the_ip = ip['origin'].split(",")[0].strip()
    return the_ip


class SgManager:
    def __init__(self, sg_id, protocol, list_of_ports):
        self.sg_id = sg_id
        self.protocol = protocol
        self.ports = list_of_ports
        self.ec2 = boto3.client('ec2')
        self.current_cidr = current_ip()+"/32"
        print("Current IP is {}".format(self.current_cidr))

    def read_sg(self):
        res = {}
        try:
            res = self.ec2.describe_security_groups(GroupIds=[self.sg_id])
        except ClientError as error:
            print(error)
            raise Exception("The Security group {} does not exists".format(self.sg_id))

        # Showing permissions
        total_ingress = len(res['SecurityGroups'][0]['IpPermissions'])
        if not total_ingress:
            print("0 permissions found")
        else:
            for ingress in res['SecurityGroups'][0]['IpPermissions']:
                print("Protocol: {0[IpProtocol]} {0[FromPort]}:{0[ToPort]}".format(ingress))
                for iprange in ingress['IpRanges']:
                    print("{0[CidrIp]} {1}".format(iprange, iprange.get("Description", "")))
        return total_ingress

    def _prepare_ip_permissions_command(self):
        ip_permissions = []
        for port in self.ports:
            ip_permissions.append(
                {
                    "FromPort":     port,
                    "ToPort":       port,
                    "IpProtocol":   self.protocol,
                    "IpRanges": [
                        {
                            "CidrIp": self.current_cidr,
                            "Description": "Generated bt SgManager"
                        }
                    ]
                }
            )
        return ip_permissions

    def enable_sg(self):
        ip_permissions = self._prepare_ip_permissions_command()
        res = self.ec2.authorize_security_group_ingress(
            GroupId=self.sg_id,
            IpPermissions = ip_permissions
        )
        return res

    def disable_sg(self):
        ip_permissions = self._prepare_ip_permissions_command()
        res = self.ec2.revoke_security_group_ingress(
            GroupId=self.sg_id,
            IpPermissions = ip_permissions
        )
        return res

    def action(self, verb):

        if verb == 'STATUS':
            values = self.read_sg()

        if verb == 'ENABLE':
            return self.enable_sg()

        if verb == 'DISABLE':
            return self.disable_sg()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="This program manages the grants of a security "
                                                 "group based on your IP")
    parser.add_argument("sg", help="The security group")
    parser.add_argument("proto", help="The protocol tcp|udp|icmp|-1", default="tcp")
    parser.add_argument("p", help="list of ports to open", default=[22], nargs="+", type=int)
    parser.add_argument("verb",
                        help="action to do: ENABLE|DISABLE|STATUS",
                        default="ENABLE",
                        choices=["ENABLE", "DISABLE", "STATUS"])
    parser.add_argument("--profile", help="AWS Profile to use")

    args = parser.parse_args()
    if args.profile:
        print("working with the profile: {}".format(args.profile))
        boto3.setup_default_session(profile_name=args.profile)

    sm = SgManager(sg_id=args.sg, protocol=args.proto, list_of_ports=args.p)
    sm.action(args.verb)

