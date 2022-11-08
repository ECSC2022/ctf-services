#!/usr/bin/env python3
import logging
from typing import Tuple
import asyncio
import string
from random import randint, choices
from time import sleep

#import requests
from ctf_gameserver import checkerlib
from ctf_gameserver.checkerlib import CheckResult

from cantinautils import orderflow


class CantinaChecker1(checkerlib.BaseChecker):
    def __init__(self, ip: str, team: int):
        super().__init__(ip, team)
        self.ip = ip
        self.gw_port = 10020
        self.pos_port = 10021
        self.timeout = 5  
        self.flagsecret = "2efada9e312fb6e690aad724eaeaf6ba83de"  
        self.baseurl = f"http://{self.ip}:{self.pos_port}"

    def place_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)

        # Try two times
        loop_error = None
        for _ in range(2):
            try:
                order_info = asyncio.run(
                    orderflow.place_order(self.baseurl, flag, False)
                )

                logging.info("Got order response: %s", order_info)
                if (oid := order_info.get("order_id", None)) != None:
                    checkerlib.set_flagid(oid)
                    checkerlib.store_state(f"order-info_{tick}", order_info)
                    return CheckResult.OK, ""
            except orderflow.TicketEndpointDown as e:
                logging.warning(e)
                msg = "Ticket endpoint is down"
                loop_error = (CheckResult.DOWN, msg)
            except orderflow.OrderCreationError as e:
                logging.warning(e)
                msg = "Order creation endpoint is down"
                loop_error = (CheckResult.DOWN, msg)
            except orderflow.TicketCreationError as e:
                logging.warning(e)
                msg = "Error during PoW ticket creation"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.PoWEndpointError as e:
                logging.warning(e)
                msg = "Faulty PoW endpoint"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.ItemEndpointError as e:
                logging.warning(e)
                msg = "Faulty order item lookup endpoint"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.OrderRetrievalError as e:
                logging.warning(e)
                msg = "Could not retrieve order"
                loop_error = (CheckResult.FAULTY, msg)

        # If there is an error in the loop, return
        if loop_error is not None:
            status, msg = loop_error
            return status, msg

        logging.warning("Could not place order.")
        return CheckResult.FAULTY, "incorrect order response"

    def check_service(self) -> Tuple[CheckResult, str]:

        # Try two times
        loop_error = None
        for _ in range(2):
            try:
                # Randomize strings here
                k = randint(15, 30)
                note = ''.join(choices(string.ascii_lowercase, k=k))
                order_info = asyncio.run(
                    orderflow.place_order(
                        self.baseurl,
                        note,
                        True,
                    )
                )
                if order_info is None or "auth_key" not in order_info:
                    raise orderflow.OrderCreationError(
                        500, repr(order_info))

                sleep(randint(1, 2))

                order_info = asyncio.run(
                    orderflow.query_order(
                        self.ip, self.gw_port, self.baseurl, order_info
                    )
                )

                # Everything went fine
                break
            except orderflow.TicketEndpointDown as e:
                logging.warning(e)
                msg = "Ticket endpoint is down"
                loop_error = (CheckResult.DOWN, msg)
            except orderflow.OrderCreationError as e:
                logging.warning(e)
                msg = "Order creation endpoint is down"
                loop_error = (CheckResult.DOWN, msg)
            except orderflow.TicketCreationError as e:
                logging.warning(e)
                msg = "Error during PoW ticket creation"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.PoWEndpointError as e:
                logging.warning(e)
                msg = "Faulty PoW endpoint"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.ItemEndpointError as e:
                logging.warning(e)
                msg = "Faulty order item lookup endpoint"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.OrderRetrievalError as e:
                logging.warning(e)
                msg = "Could not retrieve order"
                loop_error = (CheckResult.FAULTY, msg)

        # If there is an error in the loop, return
        if loop_error is not None:
            status, msg = loop_error
            return status, msg

        return CheckResult.OK, ""

    def check_flag(self, tick: int) -> Tuple[CheckResult, str]:
        flag = checkerlib.get_flag(tick)
        flagid = checkerlib.get_flagid(tick)

        order_info = checkerlib.load_state(f"order-info_{tick}")

        if not flagid:
            logging.info("No flagid saved for this team and tick")
            return (
                CheckResult.FLAG_NOT_FOUND,
                "flag was not placed successfully",
            )

        # Try two times
        order_data = None
        loop_error = None
        for _ in range(2):
            try:
                order_data = asyncio.run(
                    orderflow.query_order(
                        self.ip, self.gw_port, self.baseurl, order_info
                    )
                )

                logging.info("Got Order info: %s", order_data)
                if flag == order_data[1]:
                    return CheckResult.OK, ""
                else:
                    logging.warning(
                        "Got incorrect flag %s",
                        order_data[1]
                    )
                    return CheckResult.FLAG_NOT_FOUND, \
                            "flag was not in response"
            except orderflow.TicketEndpointDown as e:
                logging.warning(e)
                msg = "Ticket endpoint is down"
                loop_error = (CheckResult.DOWN, msg)
            except orderflow.OrderCreationError as e:
                logging.warning(e)
                msg = "Order creation endpoint is down"
                loop_error = (CheckResult.DOWN, msg)
            except orderflow.TicketCreationError as e:
                logging.warning(e)
                msg = "Error during PoW ticket creation"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.PoWEndpointError as e:
                logging.warning(e)
                msg = "Faulty PoW endpoint"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.ItemEndpointError as e:
                logging.warning(e)
                msg = "Faulty order item lookup endpoint"
                loop_error = (CheckResult.FAULTY, msg)
            except orderflow.OrderRetrievalError as e:
                logging.warning(e)
                msg = "Could not retrieve order"
                loop_error = (CheckResult.FAULTY, msg)

        # If there is an error in the loop, return
        if loop_error is not None:
            status, msg = loop_error
            return status, msg

        return CheckResult.FLAG_NOT_FOUND, "flag was not in response"


if __name__ == "__main__":
    checkerlib.run_check(CantinaChecker1)
