# ceph-ansible-copilot
Guided text based installation UI, that runs ceph-ansible. The goal of the project is to provide a UI over the top of the complexity of ceph-ansible. Users new to Ceph may then interact with the UI to build their first Ceph cluster instead of first building up their Ansible knowledge.  

## Project Status
Does it work? Well in my testing, the short answer is **YES** but it needs a heap more testing on more varied configurations!

The UI elements are all in place, as is the Ansible playbook integration and updates of the Ansible yml files.  

## What does it look like?
Here's an example run that illustrates the workflow for a small cluster of 3 nodes.  

![copilot in action](screenshots/copilot.gif)

A more detailed demo can be found on my [blog](http://opensource-storage.blogspot.co.nz/2017/12/want-to-install-ceph-but-afraid-of.html) and there are some screenshots showing the welcome page across the major distros in the screenshots folder.    

## Features  
### 0.9.6  
- Added support for container based deployments  
- minor UI tweaks (Credentials validation page)  
- callback options that may be present in ansible.cfg are temporarily removed to prevent conflicts  

### 0.9.5  
- Added ssh credentials workflow  
  - hosts selected are checked for passwordless ssh access (root only at the moment)  
  - for hosts that fail the ssh check, the admin may enter a root password common to all hosts or specify a password per host  
  - copilot uses the passwords(s) provided to setup passwordless ssh  
  - once all hosts have passed the ssh check, the UI continues to the next page (host validation)  
- the UI's color palette is based on the Linux distribution

### 0.9.2
- perform cluster & host sanity checks (primarily useful for prod deployments)  
  - support two deployment modes - production and development  
  - the mode is selected using a *--mode* switch when copilot is started   
  - in **dev** mode, pretty much anything is allowed (the default!)   
  - in **prod** mode;  
    - confirm the number of hosts are appropriate for the intended role  
    - confirm host specs are appropriate (e.g. cpu core count matches #disks for OSD hosts)  
    - prevent ceph daemon collocation  

### 0.9.1
- supports the following ceph roles; MONs, OSDs, radosgw and MDS
- defaults to a cluster name of 'ceph' (use --cluster-name=<wah> to override)
- allows selection of OSD type, encryption, hosts and installation source
- validates deployment user exists (locally)
- hosts may be specified by name or mask
- hosts are checked for DNS (2s dns lookup timeout per host - default)
- hosts are checked for passwordless ssh
- candidate hosts are probed (using Ansible)
  - host specs are shown
  - hosts are validated against the intended role
- public and cluster networks are detected from the host probe
- admin may choose which networks are used based on the ones detected  
- rgw interface defaults to the NIC on the public network in this release  
- uses plugins to create ceph-ansible group_vars files
- performs host sanity checks to confirm the host spec is appropriate for the intended role  
- deployment playbook may be passed at run time
  - if the playbook file does not exist, the program aborts before starting
the deployment process is tracked 'live' in the UI
- if the deployment fails,
  - the playbook may be rerun from the UI
  - playbook failures are shown in the UI (hostname and stderr)
- deployment playbook output is logged to a file for diagnostics (in addition
to the normal /var/log/ansible.log file)  


## How do I install and run it?  
### Requirements
- ansible-2.4.x (tested against 2.4.1 and 2.4.2)  
- python-urwid  
- python2-paramiko
- python-yaml
- python-setuptools  
- ceph-ansible - tested against Master (Dec 2017)    

For 2.4.x of Ansible you may need to enable additional repositories depending on your distribution.
- **RHEL** - enable extras with  
```bash
subscription-manager repos --enable=rhel-7-server-extras-rpms
```
- **Ubuntu** - enable the ansible ppa with  
```bash
apt-add-repository ppa:ansible/ansible
```  

#### Notes
1. All testing has been done against **CentOS7**
2. 'copilot' is tied to the Ansible 2.4.x python API. Attempting to use an older version of Ansible will fail.

### Installation process  
1. download the archive to your ansible server  
2. extract the archive and 'cd' to it  
3. run the setup program  
```bash
> python setup.py install --record files.txt  
```  
4. to run copilot
```bash
> cd /usr/share/ceph-ansible  
> copilot
```  

Notes.
- You need to cd to the ceph-ansible directory, since the playbook needs to reference ceph-ansibles roles, actions etc  
- If you're not using the root account, you'll need to use **sudo** for steps 3 and 4.

## What's next?  
Here's some ideas on how copilot could evolve;    
1. support non-root user Installation
2. support iSCSI gateways role  
3. post install configuration..what about enabling add-on pages through plugins for radosgw config for example.   
4. add more debug information to improve support (e.g. ansible messages, host information)  

## Longer term...  
Crystal ball gazing - why not take this workflow to a cockpit plugin to provide a web frontend to the ceph-ansible installation process? *Now that would be cool!*
