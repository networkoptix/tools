tests:

  scalability_test:
    merge_timeout: 1h
    host_list:
      - name: kappa
        address: 192.168.20.3
        username: jenkins
        key_path: /home/jenkins/.ssh/id_rsa
        dir: /home/jenkins/scalability
        server_bind_address: 192.168.20.3
        server_port_base: 7001
        lws_port_base: 8001
      - name: sigma
        address: 192.168.20.4
        username: jenkins
        key_path: /home/jenkins/.ssh/id_rsa
        dir: /home/jenkins/scalability
        server_bind_address: 192.168.20.4
        server_port_base: 7001
