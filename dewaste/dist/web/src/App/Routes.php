<?php

namespace App;

final class Routes
{
    public const INDEX = "/";
    public const ABOUT = "/about";
    public const FAQ = "/faq";
    public const RANKING = "/ranking";
    public const ANALYZE = "/analyze";

    public const USER_LOGIN = "/user/login";
    public const USER_LOGOUT = "/user/logout";

    public const RECYCLE_BASE = "/recycle";
    public const RECYCLE_DIGITAL = self::RECYCLE_BASE . "/digital";
    public const RECYCLE_PHYSICAL_REGISTER = self::RECYCLE_BASE . "/physical/register";
    public const RECYCLE_DIGITAL_REGISTER = self::RECYCLE_BASE . "/digital/upload";
    public const RECYCLE_MYITEMS = self::RECYCLE_BASE . "/myitems";

    public const _RECYCLE_MYITEMS_PHYSICAL = self::RECYCLE_MYITEMS . "/physical/(\d+)";
    public const _RECYCLE_MYITEMS_DIGITAL = self::RECYCLE_MYITEMS . "/digital/(\d+)";

    public static function recycleMyItemsPhysical(int $id, ?string $authToken = null): string
    {
        $query = "";
        if ($authToken != null) {
            $query = "?authToken=" . rawurlencode($authToken);
        }
        return self::RECYCLE_MYITEMS . "/physical/$id" . $query;
    }

    public static function recycleMyItemsDigital(int $id, ?string $authToken = null): string
    {
        $query = "";
        if ($authToken != null) {
            $query = "?authToken=" . rawurlencode($authToken);
        }
        return self::RECYCLE_MYITEMS . "/digital/$id" . $query;
    }

    public const _DIGITAL_ITEM_DOWNLOAD = self::RECYCLE_MYITEMS . "/digital/(\d+)/download";

    public static function digitalItemDownload(int $id, ?string $authToken = null): string
    {
        $query = "";
        if ($authToken != null) {
            $query = "?authToken=" . rawurlencode($authToken);
        }
        return self::RECYCLE_MYITEMS . "/digital/$id/download" . $query;
    }
}
