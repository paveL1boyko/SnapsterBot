from datetime import datetime

from pydantic import BaseModel


class CurrentLeague(BaseModel):
    leagueId: int
    title: str
    requiredNumberOfPointsToAchieve: int
    bonusPoints: int
    miningSpeed: float
    iconName: str
    status: str


class UserData(BaseModel):
    id: int
    username: str
    telegramId: str
    pointsCount: int
    referralCode: str
    referralId: int | None
    lastReferralPointsClaimDate: datetime
    dailyBonusStreakCount: int
    lastDailyBonusClaimDate: datetime | None = None
    lastMiningBonusClaimDate: datetime
    lastDailyCheckInClaimDate: datetime | None = None
    miningBoostCount: int
    walletAddress: str | None = None
    isWalletConnected: bool
    isWalletSigned: bool
    isWalletSignLoading: bool
    # currentLeague: CurrentLeague


class QuestModel(BaseModel):
    id: int
    questId: int
    title: str
    subtitle: str
    iconName: str
    bonusPoints: int
    category: str
    type: str
    link: str | None
    referralThreshold: int | None = None
    miningBoostThreshold: int | None = None
    status: str
