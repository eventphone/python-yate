import unittest
from yate import protocol


class BaseEncodingTestCases(unittest.TestCase):
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


class MessageDeserializationTestCases(unittest.TestCase):
    def test_parse_yate_msg(self):
        result = protocol.parse_yate_message('%%>message:0x7ff823883bb0.1932044751:1522601502:call.execute::id=sip/151:module=sip:status=incoming:address=172.20.23.1%z5060:billid=1522598913-105:answered=false:direction=incoming:callid=sip/4265e70a902406405ac10e1e275@DSIP/f-9024064014ea27935f/:caller=9940 DebügDÄCT:called=2049:callername=DebügDÄCT:antiloop=19:ip_host=172.20.23.1:ip_port=5060:ip_transport=UDP:connection_id=dect:connection_reliable=false:sip_uri=sip%z2049@172.20.23.2:sip_from=sip%z9940@172.20.23.2:sip_to=<sip%z2049@172.20.23.2>:sip_callid=4265e70a902406405ac10e1e275@DSIP:device=Mitel SIP-DECT (SW-Version=7.1-CK14):sip_contact="DebügDÄCT" <sip%z9940@172.20.1.3>;+sip.instance="<urn%zuuid%z1F102AF1-2C00-0100-8000-03029649cf19>":sip_supported=replaces, 100rel, path, gruu:sip_user-agent=Mitel SIP-DECT (SW-Version=7.1-CK14):sip_allow=INVITE, ACK, OPTIONS, CANCEL, BYE, REFER, NOTIFY, INFO, MESSAGE, UPDATE, PRACK:sip_content-type=application/sdp:username=9940:realm=voip.eventphone.de:newcall=true:domain=172.20.23.2:xsip_nonce_age=0:rtp_addr=172.20.23.12:media=yes:formats=alaw,mulaw:transport=RTP/AVP:rtp_rfc2833=101:rtp_port=16326:sdp_silenceSupp=off - - - -:sdp_sendrecv=:sdp_fmtp%z=0-15:rtp_forward=yes:handlers=javascript%z15,regexroute%z40,regexroute%z100,javascript%z15,cdrbuild%z50,regexroute%z80,regexroute%z100,sip%z100,register%z120:context=default:oconnection_id=dect:osip_X-EventphoneID=f45a42b9-35cc-11e8-b1ae-000c2991f54c:osip_X-CallType=default:callto=sip/sip%z2049@172.20.1.3'.encode("utf-8"))
        self.assertEqual("message", result.msg_type)
        self.assertEqual('0x7ff823883bb0.1932044751', result.id)
        self.assertEqual(1522601502, result.time)
        self.assertEqual('call.execute', result.name)
        self.assertEqual('DebügDÄCT', result.params['callername'])
        self.assertEqual(False, result.reply)

    def test_parse_yate_msg_without_kv(self):
        result = protocol.parse_yate_message('%%>message:0x7ff823883bb0.1932044751:1522601502:call.execute:'.encode("utf-8"))
        self.assertEqual("message", result.msg_type)
        self.assertEqual('0x7ff823883bb0.1932044751', result.id)
        self.assertEqual(1522601502, result.time)
        self.assertEqual('call.execute', result.name)
        self.assertEqual({}, result.params)
        self.assertEqual(False, result.reply)

    def test_parse_install_message(self):
        result = protocol.parse_yate_message(b"%%<install:50:test:true")
        self.assertEqual("install", result.msg_type)
        self.assertEqual(50, result.priority)
        self.assertEqual("test", result.name)
        self.assertEqual(True, result.success)

    def test_parse_install_request_no_filter(self):
        result = protocol.parse_yate_message(b"%%>install:70:chan.test")
        self.assertEqual(result.priority, 70)
        self.assertEqual(result.name, "chan.test")

    def test_parse_install_request(self):
        result = protocol.parse_yate_message(b"%%>install:70:chan.test:important:true")
        self.assertEqual(result.priority, 70)
        self.assertEqual(result.name, "chan.test")
        self.assertEqual(result.filter_name, "important")
        self.assertEqual(result.filter_value, "true")

    def test_parse_uninstall_request(self):
        result = protocol.parse_yate_message(b"%%>uninstall:test")
        self.assertEqual(result.name, "test")

    def test_parse_uninstall_message(self):
        result = protocol.parse_yate_message(b"%%<uninstall:50:test:true")
        self.assertEqual("uninstall", result.msg_type)
        self.assertEqual(50, result.priority)
        self.assertEqual("test", result.name)
        self.assertEqual(True, result.success)

    def test_parse_watch_request(self):
        result = protocol.parse_yate_message(b"%%>watch:test")
        self.assertEqual(result.name, "test")

    def test_parse_watch_message(self):
        result = protocol.parse_yate_message(b"%%<watch:call.execute:false")
        self.assertEqual("watch", result.msg_type)
        self.assertEqual("call.execute", result.name)
        self.assertEqual(False, result.success)

    def test_parse_unwatch_request(self):
        result = protocol.parse_yate_message(b"%%>unwatch:test")
        self.assertEqual(result.name, "test")

    def test_parse_unwatch_message(self):
        result = protocol.parse_yate_message(b"%%<unwatch:call.execute:true")
        self.assertEqual("unwatch", result.msg_type)
        self.assertEqual("call.execute", result.name)
        self.assertEqual(True, result.success)

    def test_parse_setlocal_message(self):
        result = protocol.parse_yate_message(b"%%>setlocal:id:mychan0")
        self.assertEqual("setlocal", result.msg_type)
        self.assertEqual("id", result.param)
        self.assertEqual("mychan0", result.value)

    def test_parse_setlocal_param_request_message(self):
        result = protocol.parse_yate_message(b"%%>setlocal:engine.version:")
        self.assertEqual("setlocal", result.msg_type)
        self.assertEqual("engine.version", result.param)
        self.assertEqual("", result.value)

    def test_parse_setlocal_positive_answer(self):
        result = protocol.parse_yate_message(b"%%<setlocal:id:mychan0:true")
        self.assertEqual("setlocal", result.msg_type)
        self.assertEqual("id", result.param)
        self.assertEqual("mychan0", result.value)
        self.assertTrue(result.success)

    def test_parse_setlocal_negative_answer(self):
        result = protocol.parse_yate_message(b"%%<setlocal:id:oldchan:false")
        self.assertEqual("setlocal", result.msg_type)
        self.assertEqual("id", result.param)
        self.assertEqual("oldchan", result.value)
        self.assertFalse(result.success)


class MessageSerializationTestCases(unittest.TestCase):
    def test_encode_yate_install_mgs(self):
        message = protocol.InstallRequest(1, "call.execute")
        result = message.encode()
        self.assertEqual(b'%%>install:1:call.execute', result)

    def test_encode_yate_install_mgs_filter(self):
        message = protocol.InstallRequest(1, "call.execute", "test1", "test2")
        result = message.encode()
        self.assertEqual(b'%%>install:1:call.execute:test1:test2', result)

    def test_encode_yate_msg(self):
        result = protocol.parse_yate_message('%%>message:0x7ff823883bb0.1932044751:1522601502:call.execute::id=sip/151:module=sip:status=incoming:address=172.20.23.1%z5060:billid=1522598913-105:answered=false:direction=incoming:callid=sip/4265e70a902406405ac10e1e275@DSIP/f-9024064014ea27935f/:caller=9940 DebügDÄCT:called=2049:callername=DebügDÄCT:antiloop=19:ip_host=172.20.23.1:ip_port=5060:ip_transport=UDP:connection_id=dect:connection_reliable=false:sip_uri=sip%z2049@172.20.23.2:sip_from=sip%z9940@172.20.23.2:sip_to=<sip%z2049@172.20.23.2>:sip_callid=4265e70a902406405ac10e1e275@DSIP:device=Mitel SIP-DECT (SW-Version=7.1-CK14):sip_contact="DebügDÄCT" <sip%z9940@172.20.1.3>;+sip.instance="<urn%zuuid%z1F102AF1-2C00-0100-8000-03029649cf19>":sip_supported=replaces, 100rel, path, gruu:sip_user-agent=Mitel SIP-DECT (SW-Version=7.1-CK14):sip_allow=INVITE, ACK, OPTIONS, CANCEL, BYE, REFER, NOTIFY, INFO, MESSAGE, UPDATE, PRACK:sip_content-type=application/sdp:username=9940:realm=voip.eventphone.de:newcall=true:domain=172.20.23.2:xsip_nonce_age=0:rtp_addr=172.20.23.12:media=yes:formats=alaw,mulaw:transport=RTP/AVP:rtp_rfc2833=101:rtp_port=16326:sdp_silenceSupp=off - - - -:sdp_sendrecv=:sdp_fmtp%z=0-15:rtp_forward=yes:handlers=javascript%z15,regexroute%z40,regexroute%z100,javascript%z15,cdrbuild%z50,regexroute%z80,regexroute%z100,sip%z100,register%z120:context=default:oconnection_id=dect:osip_X-EventphoneID=f45a42b9-35cc-11e8-b1ae-000c2991f54c:osip_X-CallType=default:callto=sip/sip%z2049@172.20.1.3'.encode("utf-8"))
        result = result.encode_answer_for_yate(False)
        real_example_answer = '%%<message:0x7ff823883bb0.1932044751:false:call.execute::id=sip/151:module=sip:status=incoming:address=172.20.23.1%z5060:billid=1522598913-105:answered=false:direction=incoming:callid=sip/4265e70a902406405ac10e1e275@DSIP/f-9024064014ea27935f/:caller=9940 DebügDÄCT:called=2049:callername=DebügDÄCT:antiloop=19:ip_host=172.20.23.1:ip_port=5060:ip_transport=UDP:connection_id=dect:connection_reliable=false:sip_uri=sip%z2049@172.20.23.2:sip_from=sip%z9940@172.20.23.2:sip_to=<sip%z2049@172.20.23.2>:sip_callid=4265e70a902406405ac10e1e275@DSIP:device=Mitel SIP-DECT (SW-Version=7.1-CK14):sip_contact="DebügDÄCT" <sip%z9940@172.20.1.3>;+sip.instance="<urn%zuuid%z1F102AF1-2C00-0100-8000-03029649cf19>":sip_supported=replaces, 100rel, path, gruu:sip_user-agent=Mitel SIP-DECT (SW-Version=7.1-CK14):sip_allow=INVITE, ACK, OPTIONS, CANCEL, BYE, REFER, NOTIFY, INFO, MESSAGE, UPDATE, PRACK:sip_content-type=application/sdp:username=9940:realm=voip.eventphone.de:newcall=true:domain=172.20.23.2:xsip_nonce_age=0:rtp_addr=172.20.23.12:media=yes:formats=alaw,mulaw:transport=RTP/AVP:rtp_rfc2833=101:rtp_port=16326:sdp_silenceSupp=off - - - -:sdp_sendrecv=:sdp_fmtp%z=0-15:rtp_forward=yes:handlers=javascript%z15,regexroute%z40,regexroute%z100,javascript%z15,cdrbuild%z50,regexroute%z80,regexroute%z100,sip%z100,register%z120:context=default:oconnection_id=dect:osip_X-EventphoneID=f45a42b9-35cc-11e8-b1ae-000c2991f54c:osip_X-CallType=default:callto=sip/sip%z2049@172.20.1.3'.encode("utf-8")
        result_split = result.split(b":")
        real_example_split = real_example_answer.split(b":")
        self.assertListEqual(real_example_split[0:4], result_split[0:4])
        self.assertSetEqual(set(real_example_split[5:]), set(result_split[5:]))

    def test_encode_yate_message_changed(self):
        result = protocol.parse_yate_message(b"%%>message:id123:4711:call.execute:old_return:test=yes")
        result.params["test"] = "false"
        result.return_value = "new_return"
        encodedMsg = result.encode_answer_for_yate(True)
        self.assertEqual(b"%%<message:id123:true:call.execute:new_return:test=false", encodedMsg)

    def test_encode_new_yate_message(self):
        msg = protocol.MessageRequest("call.execute", {"caller": "nick"}, "")
        result = msg.encode("id-4908", 4711)
        self.assertEqual(b"%%>message:id-4908:4711:call.execute::caller=nick", result)

    def test_encode_new_yate_message_no_params(self):
        msg = protocol.MessageRequest("call.execute", {}, "")
        result = msg.encode("id-4908", 4712)
        self.assertEqual(b"%%>message:id-4908:4712:call.execute:", result)

    def test_encode_install_message(self):
        msg = protocol.InstallRequest("100", "call.hangup")
        result = msg.encode()
        self.assertEqual(b"%%>install:100:call.hangup", result)

    def test_encode_install_message_with_filter(self):
        msg = protocol.InstallRequest("100", "chan.hangup", "caller", "nick")
        result = msg.encode()
        self.assertEqual(b"%%>install:100:chan.hangup:caller:nick", result)

    def test_encode_install_confirm(self):
        msg = protocol.InstallConfirm(80, "chan.test", True)
        result = msg.encode()
        self.assertEqual(b"%%<install:80:chan.test:true", result)

    def test_encode_uninstall_message(self):
        msg = protocol.UninstallRequest("chan.hangup")
        result = msg.encode()
        self.assertEqual(b"%%>uninstall:chan.hangup", result)

    def test_encode_uninstall_confirm(self):
        msg = protocol.UninstallConfirm(80, "chan.test", True)
        result = msg.encode()
        self.assertEqual(b"%%<uninstall:80:chan.test:true", result)

    def test_encode_watch_message(self):
        msg = protocol.WatchRequest("chan.dtmf")
        result = msg.encode()
        self.assertEqual(b"%%>watch:chan.dtmf", result)

    def test_encode_watch_confirm(self):
        msg = protocol.WatchConfirm("chan.dtmf", True)
        result = msg.encode()
        self.assertEqual(b"%%<watch:chan.dtmf:true", result)

    def test_encode_unwatch_message(self):
        msg = protocol.UnwatchRequest("chan.dtmf")
        result = msg.encode()
        self.assertEqual(b"%%>unwatch:chan.dtmf", result)

    def test_encode_unwatch_confirm(self):
        msg = protocol.UnwatchConfirm("chan.dtmf", True)
        result = msg.encode()
        self.assertEqual(b"%%<unwatch:chan.dtmf:true", result)

    def test_encode_setlocal_request(self):
        msg = protocol.SetLocalRequest("id", "mychan0")
        result = msg.encode()
        self.assertEqual(b"%%>setlocal:id:mychan0", result)

    def test_encode_setlocal_request_query_param(self):
        msg = protocol.SetLocalRequest("engine.version")
        result = msg.encode()
        self.assertEqual(b"%%>setlocal:engine.version:", result)

    def test_encode_setlocal_answer_success(self):
        msg = protocol.SetLocalAnswer("id", "mychan0", True)
        result = msg.encode()
        self.assertEqual(b"%%<setlocal:id:mychan0:true", result)

    def test_encode_setlocal_answer_failed(self):
        msg = protocol.SetLocalAnswer("id", "oldchan", False)
        result = msg.encode()
        self.assertEqual(b"%%<setlocal:id:oldchan:false", result)

    def test_encode_connect_message(self):
        msg = protocol.ConnectToYate()
        result = msg.encode()
        self.assertEqual(b"%%>connect:global", result)


if __name__ == '__main__':
    unittest.main()
