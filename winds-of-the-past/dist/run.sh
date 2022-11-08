cron
socat -T180 tcp-l:10060,reuseaddr,fork EXEC:/service,pty,stderr,echo=0
