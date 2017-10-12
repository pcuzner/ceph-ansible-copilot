# ceph-ansible-copilot
Guided text based installation UI, that runs ceph-ansible. The goal of the project is to provide a UI over the top of the complexity of ceph-ansible. Users new to Ceph may then interact with the UI to build their first Ceph cluster instead of first building up their Ansible knowledge.  

# Features  
- accepts cluster name, osd type and hosts
- hosts may be specified by name or mask
- hosts are checked for dns (2s dns lookup timeout per host)
- hosts are checked for passwordless ssh
- candidate hosts are probed (using ansible)
  - host specs are shown
  - hosts are validated against the intended role
- public and cluster networks are detected from the host probe
- admin may choose which networks are used based on the ones detected
- deployment playbook may be passed at run time
  - if the playbook file does not exist, the program aborts before starting
- the deployment process is tracked 'live' in the UI
- if the deployment fails, the playbook may be rerun from the UI
- playbook failures are shown in the UI (hostname and stderr)
- deployment playbook output is logged to a file for diagnostics

# Status
Does it work? The short answer is **NO** not yet!  

The UI elements are all in place, as is the ansible playbook integration. The next thing to work on is the updates of the ansible yml files based on the values from the host probes and the information given in the UI.

Stay Tuned!

# What does it look like?
Here's an example run that illustrates the workflow for a small cluster of 3 nodes.

# What does it need to run?
ansible-2.0 -> 2.3 (**not 2.4**)  
ceph-ansible 
