import unittest
from yate import protocol


class EncodingTestCases(unittest.TestCase):
    def test_encode_bytes(self):
        result = protocol.yate_encode_bytes(b"test%")
        self.assertEqual( b"test%%", result)

    def test_encode_bytes2(self):
        result = protocol.yate_encode_bytes(b"/bin:/usr/bin:/usr/local/bin")
        self.assertEqual( b"/bin%z/usr/bin%z/usr/local/bin", result)

    def test_decode_bytes(self):
        result = protocol.yate_decode_bytes(b"test%%")
        self.assertEqual(b"test%" , result)

    def test_decode_bytes2(self):
        result = protocol.yate_decode_bytes(b"/bin%z/usr/bin%z/usr/local/bin")
        self.assertEqual(b"/bin:/usr/bin:/usr/local/bin" , result)

    def test_decode_fails_invalid(self):
        with self.assertRaises(Exception):
            result = protocol.yate_decode_bytes(b"/bin%:/usr/bin%:/usr/local/bin")

    def test_parse_yate_msg(self):
        result = protocol.parse_yatemessage('%%>message:0x7ff823883bb0.1932044751:1522601502:call.execute::id=sip/151:module=sip:status=incoming:address=172.20.23.1%z5060:billid=1522598913-105:answered=false:direction=incoming:callid=sip/4265e70a902406405ac10e1e275@DSIP/f-9024064014ea27935f/:caller=9940 DebügDÄCT:called=2049:callername=DebügDÄCT:antiloop=19:ip_host=172.20.23.1:ip_port=5060:ip_transport=UDP:connection_id=dect:connection_reliable=false:sip_uri=sip%z2049@172.20.23.2:sip_from=sip%z9940@172.20.23.2:sip_to=<sip%z2049@172.20.23.2>:sip_callid=4265e70a902406405ac10e1e275@DSIP:device=Mitel SIP-DECT (SW-Version=7.1-CK14):sip_contact="DebügDÄCT" <sip%z9940@172.20.1.3>;+sip.instance="<urn%zuuid%z1F102AF1-2C00-0100-8000-03029649cf19>":sip_supported=replaces, 100rel, path, gruu:sip_user-agent=Mitel SIP-DECT (SW-Version=7.1-CK14):sip_allow=INVITE, ACK, OPTIONS, CANCEL, BYE, REFER, NOTIFY, INFO, MESSAGE, UPDATE, PRACK:sip_content-type=application/sdp:username=9940:realm=voip.eventphone.de:newcall=true:domain=172.20.23.2:xsip_nonce_age=0:rtp_addr=172.20.23.12:media=yes:formats=alaw,mulaw:transport=RTP/AVP:rtp_rfc2833=101:rtp_port=16326:sdp_silenceSupp=off - - - -:sdp_sendrecv=:sdp_fmtp%z=0-15:rtp_forward=yes:handlers=javascript%z15,regexroute%z40,regexroute%z100,javascript%z15,cdrbuild%z50,regexroute%z80,regexroute%z100,sip%z100,register%z120:context=default:oconnection_id=dect:osip_X-EventphoneID=f45a42b9-35cc-11e8-b1ae-000c2991f54c:osip_X-CallType=default:callto=sip/sip%z2049@172.20.1.3'.encode("utf-8"))
        self.assertEqual('0x7ff823883bb0.1932044751', result.id)
        self.assertEqual('1522601502', result.time)
        self.assertEqual('call.execute', result.name)
        self.assertEqual('DebügDÄCT', result.params['callername'])

    def test_parse_yate_msg_without_kv(self):
        result = protocol.parse_yatemessage('%%>message:0x7ff823883bb0.1932044751:1522601502:call.execute:'.encode("utf-8"))
        self.assertEqual('0x7ff823883bb0.1932044751', result.id)
        self.assertEqual('1522601502', result.time)
        self.assertEqual('call.execute', result.name)
        self.assertEqual({}, result.params)

    def test_encode_yate_install_mgs(self):
        message = protocol.InstallToYate(1, "call.execute")
        result = message.encode()
        self.assertEqual(b'%%>install:1:call.execute', result)

    def test_encode_yate_install_mgs_filter(self):
        message = protocol.InstallToYate(1, "call.execute", "test1", "test2")
        result = message.encode()
        self.assertEqual(b'%%>install:1:call.execute:test1:test2', result)

    def test_encode_yate_msg(self):
        result = protocol.parse_yatemessage('%%>message:0x7ff823883bb0.1932044751:1522601502:call.execute::id=sip/151:module=sip:status=incoming:address=172.20.23.1%z5060:billid=1522598913-105:answered=false:direction=incoming:callid=sip/4265e70a902406405ac10e1e275@DSIP/f-9024064014ea27935f/:caller=9940 DebügDÄCT:called=2049:callername=DebügDÄCT:antiloop=19:ip_host=172.20.23.1:ip_port=5060:ip_transport=UDP:connection_id=dect:connection_reliable=false:sip_uri=sip%z2049@172.20.23.2:sip_from=sip%z9940@172.20.23.2:sip_to=<sip%z2049@172.20.23.2>:sip_callid=4265e70a902406405ac10e1e275@DSIP:device=Mitel SIP-DECT (SW-Version=7.1-CK14):sip_contact="DebügDÄCT" <sip%z9940@172.20.1.3>;+sip.instance="<urn%zuuid%z1F102AF1-2C00-0100-8000-03029649cf19>":sip_supported=replaces, 100rel, path, gruu:sip_user-agent=Mitel SIP-DECT (SW-Version=7.1-CK14):sip_allow=INVITE, ACK, OPTIONS, CANCEL, BYE, REFER, NOTIFY, INFO, MESSAGE, UPDATE, PRACK:sip_content-type=application/sdp:username=9940:realm=voip.eventphone.de:newcall=true:domain=172.20.23.2:xsip_nonce_age=0:rtp_addr=172.20.23.12:media=yes:formats=alaw,mulaw:transport=RTP/AVP:rtp_rfc2833=101:rtp_port=16326:sdp_silenceSupp=off - - - -:sdp_sendrecv=:sdp_fmtp%z=0-15:rtp_forward=yes:handlers=javascript%z15,regexroute%z40,regexroute%z100,javascript%z15,cdrbuild%z50,regexroute%z80,regexroute%z100,sip%z100,register%z120:context=default:oconnection_id=dect:osip_X-EventphoneID=f45a42b9-35cc-11e8-b1ae-000c2991f54c:osip_X-CallType=default:callto=sip/sip%z2049@172.20.1.3'.encode("utf-8"))
        result = result.encode_answer_for_yate(False)
        #self.assertEqual(''.encode("utf-8"),result)


if __name__ == '__main__':
    unittest.main()
