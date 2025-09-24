import React, { FC } from 'react';
import { Stack, Typography } from '@dubizzle/ui';
import { useDispatch } from 'react-redux';
import authContexts from '@dubizzle/auth/src/contexts';
import Image from 'next/image';
import { useFormatMessage } from '../../../hooks/intl';
import { staticUrl } from '../../../constants/urls';
import ActionButtons from '../ActionButtons';
import { setWalkInCheckinScreen } from '../../../store/reducers/sifmCheckin';
import { WALK_IN_CHECKIN_SCREEN } from '../../../constants/sifm';
import { BottomBox, CenteredStack } from './WalkInCheckInForm.styled';
import InfoText from '../InfoText';
import { requireLogin } from '../../../store/reducers/user';

const UserOrGuest: FC = () => {
  const dispatch = useDispatch();
  const t = useFormatMessage();

  const continueAsGuest = (): void => {
    dispatch(setWalkInCheckinScreen(WALK_IN_CHECKIN_SCREEN.IS_CAR_OWNER));
  };

  const validateUser = (): void => {
    dispatch(
      requireLogin({
        context: authContexts.CHECKIN,
        requiresPhoneVerification: true,
      }),
    ).then(action => {
      if (!action.error) {
        window.open('/car-appointments');
      }
    });
  };

  return (
    <CenteredStack>
      <Stack
        spacing={6}
        alignItems="center"
        justifyContent="center"
        textAlign="center"
      >
        <Typography variant="h4" fontWeight="bold" paddingX={3}>
          {t('welcomeToSalesConsultation')}
        </Typography>
        <Image
          src={`${staticUrl}/car-appointments/carOwner.png`}
          alt="Car Owner Check-in"
          width={180}
          height={180}
        />
        <InfoText text={t('onlineCheckinInfo')} />
      </Stack>

      <BottomBox>
        <ActionButtons
          onSecondaryClick={continueAsGuest}
          onPrimaryClick={validateUser}
          secondaryText={t('continueAsGuest')}
          primaryText={t('continue')}
          secondaryButtonSx={{
            flex: { xs: 1 },
          }}
          primaryButtonSx={{
            flex: { xs: 1 },
          }}
        />
      </BottomBox>
    </CenteredStack>
  );
};

export default UserOrGuest;