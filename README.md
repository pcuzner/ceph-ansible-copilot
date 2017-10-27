# ceph-ansible-copilot
Guided text based installation UI, that runs ceph-ansible. The goal of the project is to provide a UI over the top of the complexity of ceph-ansible. Users new to Ceph may then interact with the UI to build their first Ceph cluster instead of first building up their Ansible knowledge.  

## Features  
- supports the following ceph roles; mons, osds, radosgw and mds[1] 
- defaults to a cluster name of 'ceph' (use --cluster-name=<wah> to override)
- allows selection of osd type, encryption, hosts and installation source
- validates deployment user exists (locally)
- hosts may be specified by name or mask
- hosts are checked for dns (2s dns lookup timeout per host - default)
- hosts are checked for passwordless ssh
- candidate hosts are probed (using ansible)
  - host specs are shown
  - hosts are validated against the intended role
- public and cluster networks are detected from the host probe
- admin may choose which networks are used based on the ones detected  
- rgw interface defaults to the nic on the public network in this release  
- uses plugins to create ceph-ansible group_vars files
- deployment playbook may be passed at run time
  - if the playbook file does not exist, the program aborts before starting
the deployment process is tracked 'live' in the UI
- if the deployment fails,
  - the playbook may be rerun from the UI
  - playbook failures are shown in the UI (hostname and stderr)
- deployment playbook output is logged to a file for diagnostics (in addition
to the normal /var/log/ansible.log file)  

[1] mds deployments cause fail in ansible on CentOS7 + ceph-ansible (master)

## Status
Does it work? The short answer is **YES** but it needs a heap more testing on more varied configurations!

The UI elements are all in place, as is the ansible playbook integration and updates of the ansible yml files.  

What's missing...sanity checks! Since the candidate hosts are probed, the goal is to sanity check the requested configuration against the hardware.

Stay Tuned!

## What does it look like?
Here's an example run that illustrates the workflow for a small cluster of 3 nodes.  
  
![copilot in action](copilot.gif)


## What does it need to run?
ansible-2.0 -> 2.3 (**not 2.4**)  
python-urwid  
ceph-ansible 

## How do I install and run it?
1. download the archive to your ansible server  
2. extract the archive and 'cd' to it  
3. run the setup program  
```
python setup.py install --record files.txt  
```  
4. to run copilot
```
cd /usr/share/ceph-ansible  
copilot
``` 
NB. You need to cd to the ceph-ansible directory, since the playbook needs to reference ceph-ansibles roles, actions etc  

